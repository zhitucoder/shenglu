import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .. import config


class SessionStore:
    """每个音频一个会话, JSON 持久化, 进程内带锁避免并发读写竞争。"""

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self._lock = threading.RLock()

    def _path(self, session_id: str) -> Path:
        return self.session_dir / f"{session_id}.json"

    def create(self, filename: str, audio_ext: str) -> dict:
        session_id = uuid.uuid4().hex[:12]
        month = datetime.now().strftime("%Y-%m")
        audio_dir = config.AUDIO_DIR / month
        audio_dir.mkdir(parents=True, exist_ok=True)
        session = {
            "id": session_id,
            "name": Path(filename).stem,
            "filename": filename,
            "status": "processing",
            "progress": 0.0,
            "error": None,
            "duration_sec": None,
            "audio_path": str(audio_dir / f"{session_id}{audio_ext}"),
            "transcript_path": None,
            "report_path": None,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.save(session)
        return session

    def list_sessions(self) -> list[dict]:
        sessions = []
        for path in self.session_dir.glob("*.json"):
            try:
                with self._lock:
                    sessions.append(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
        return sessions

    def rename(self, session_id: str, name: str) -> Optional[dict]:
        return self.update(session_id, name=name.strip())

    def get(self, session_id: str) -> Optional[dict]:
        path = self._path(session_id)
        if not path.exists():
            return None
        with self._lock:
            return json.loads(path.read_text(encoding="utf-8"))

    def save(self, session: dict) -> None:
        with self._lock:
            self._path(session["id"]).write_text(
                json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def update(self, session_id: str, **fields) -> Optional[dict]:
        session = self.get(session_id)
        if session is None:
            return None
        session.update(fields)
        self.save(session)
        return session

    def delete(self, session_id: str) -> None:
        session = self.get(session_id)
        if session is None:
            return
        for key in ("audio_path", "transcript_path", "report_path"):
            path = session.get(key)
            if path and Path(path).exists():
                try:
                    Path(path).unlink()
                except OSError:
                    pass
        self._path(session_id).unlink(missing_ok=True)

    @staticmethod
    def write_transcript(path: Path, segments: list[dict]) -> None:
        lines = []
        for seg in segments:
            ts = f"[{_fmt_time(seg['start'])} -> {_fmt_time(seg['end'])}]"
            lines.append(f"{ts} {seg['text'].strip()}")
        path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def write_report(path: Path, report: str) -> None:
        path.write_text(report, encoding="utf-8")


def _fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
