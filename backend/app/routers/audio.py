import logging
import threading
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import config
from ..schemas import AudioStatusResponse, RenameRequest, UploadResponse
from ..services import asr, storage

logger = logging.getLogger("audio")
router = APIRouter(prefix="/api/audio", tags=["audio"])

ALLOWED_EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".mp4", ".wma"}
store = storage.SessionStore(config.SESSION_DIR)
_workers: dict[str, threading.Thread] = {}


def _worker(session_id: str) -> None:
    session = store.get(session_id)
    if session is None:
        return
    audio_path = Path(session["audio_path"])
    start = time.time()
    try:
        lines = []
        for item in asr.transcribe(audio_path):
            count, duration, _info, seg = item
            if count is None:
                break
            lines.append(seg)
            if duration > 0:
                store.update(session_id, progress=min(0.99, seg["end"] / duration))
            else:
                store.update(session_id, progress=min(0.99, count * 0.01))
        transcript_path = config.TRANSCRIPT_DIR / f"{session_id}.md"
        storage.SessionStore.write_transcript(transcript_path, lines)
        store.update(
            session_id,
            status="done",
            progress=1.0,
            duration_sec=round(time.time() - start, 1),
            transcript_path=str(transcript_path),
        )
    except Exception as exc:
        logger.exception("transcribe failed for %s", session_id)
        store.update(session_id, status="failed", error=str(exc))


def _get_session(session_id: str) -> dict:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(404, "音频不存在")
    return session


def _download_path(session_id: str, key: str) -> Path:
    session = _get_session(session_id)
    path = session.get(key)
    if not path or not Path(path).exists():
        raise HTTPException(404, "文件不存在或尚未生成")
    return Path(path)


@router.post("", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"不支持的文件类型: {ext or '未知'}, 支持 {sorted(ALLOWED_EXT)}")
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"文件超过 {config.MAX_UPLOAD_MB}MB 限制")
    session = store.create(file.filename, ext)
    Path(session["audio_path"]).write_bytes(data)
    thread = threading.Thread(target=_worker, args=(session["id"],), daemon=True)
    _workers[session["id"]] = thread
    thread.start()
    return UploadResponse(id=session["id"], status=session["status"], filename=file.filename)


@router.get("/{session_id}", response_model=AudioStatusResponse)
def get_status(session_id: str):
    session = _get_session(session_id)
    resp = AudioStatusResponse(
        id=session["id"],
        name=session.get("name"),
        filename=session.get("filename"),
        status=session["status"],
        progress=session["progress"],
        error=session.get("error"),
        duration_sec=session.get("duration_sec"),
        created_at=session.get("created_at"),
    )
    path = session.get("transcript_path")
    if path and Path(path).exists():
        text = Path(path).read_text(encoding="utf-8")
        resp.transcript = text
    return resp


@router.patch("/{session_id}")
def rename_session(session_id: str, body: RenameRequest):
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "名称不能为空")
    session = store.rename(session_id, name)
    if session is None:
        raise HTTPException(404, "音频不存在")
    return {"id": session_id, "name": session["name"]}


@router.get("/{session_id}/transcript/download")
def download_transcript(session_id: str):
    path = _download_path(session_id, "transcript_path")
    session = _get_session(session_id)
    return FileResponse(
        path,
        media_type="text/markdown",
        filename=f"{session.get('name', session_id)}_原文.md",
    )


@router.get("/{session_id}/report/download")
def download_report(session_id: str):
    path = _download_path(session_id, "report_path")
    session = _get_session(session_id)
    return FileResponse(
        path,
        media_type="text/markdown",
        filename=f"{session.get('name', session_id)}_总结报告.md",
    )
