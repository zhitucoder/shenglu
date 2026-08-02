from pathlib import Path

from fastapi import APIRouter, HTTPException

from .. import config
from ..schemas import ChatRequest, ChatResponse
from ..services import db, llm, storage

router = APIRouter(prefix="/api/audio/{session_id}/chat", tags=["chat"])

store = storage.SessionStore(config.SESSION_DIR)


def _require_transcript(session_id: str) -> str:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(404, "音频不存在")
    tpath = session.get("transcript_path")
    if not tpath or not Path(tpath).exists():
        raise HTTPException(409, "转写尚未完成, 请稍后再试")
    return Path(tpath).read_text(encoding="utf-8")


@router.post("", response_model=ChatResponse)
def chat(session_id: str, body: ChatRequest):
    transcript = _require_transcript(session_id)
    history = db.get_messages(session_id)
    try:
        answer = llm.chat(transcript, history, body.question)
    except Exception as exc:
        return ChatResponse(answer="", error=str(exc))
    db.add_message(session_id, "user", body.question)
    db.add_message(session_id, "assistant", answer)
    return ChatResponse(answer=answer)


@router.get("")
def get_history(session_id: str):
    if store.get(session_id) is None:
        raise HTTPException(404, "音频不存在")
    return db.get_messages(session_id)
