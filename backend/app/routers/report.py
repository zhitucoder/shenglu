import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

from .. import config
from ..schemas import ReportResponse
from ..services import llm, storage

router = APIRouter(prefix="/api/audio/{session_id}/report", tags=["report"])

store = storage.SessionStore(config.SESSION_DIR)
_running: set[str] = set()
_running_lock = threading.Lock()


def _worker(session_id: str) -> None:
    session = store.get(session_id)
    transcript = ""
    try:
        if session is None:
            raise RuntimeError("音频不存在")
        tpath = session.get("transcript_path")
        if not tpath or not Path(tpath).exists():
            raise RuntimeError("转写尚未完成, 请先等待转写结束")
        transcript = Path(tpath).read_text(encoding="utf-8")
        report = llm.generate_summary(transcript)
        report_path = config.REPORT_DIR / f"{session_id}.md"
        storage.SessionStore.write_report(report_path, report)
        store.update(session_id, report_path=str(report_path))
    except Exception as exc:
        store.update(session_id, error=f"生成报告失败: {exc}")
    finally:
        with _running_lock:
            _running.discard(session_id)


@router.post("", response_model=ReportResponse)
def generate_report(session_id: str):
    session = store.get(session_id)
    if session is None:
        raise HTTPException(404, "音频不存在")
    tpath = session.get("transcript_path")
    if not tpath or not Path(tpath).exists():
        raise HTTPException(409, "转写尚未完成, 请稍后再试")
    with _running_lock:
        if session_id in _running:
            return ReportResponse(id=session_id, error="报告正在生成中, 请稍候")
        _running.add(session_id)
    threading.Thread(target=_worker, args=(session_id,), daemon=True).start()
    return ReportResponse(id=session_id)


@router.get("", response_model=ReportResponse)
def get_report(session_id: str):
    session = store.get(session_id)
    if session is None:
        raise HTTPException(404, "音频不存在")
    with _running_lock:
        generating = session_id in _running
    path = session.get("report_path")
    if path and Path(path).exists():
        return ReportResponse(id=session_id, report=Path(path).read_text(encoding="utf-8"))
    if generating:
        return ReportResponse(id=session_id, error="报告正在生成中")
    return ReportResponse(id=session_id, error=session.get("error"))
