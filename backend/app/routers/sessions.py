from fastapi import APIRouter

from .. import config
from ..schemas import SessionListItem
from ..services import storage

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

store = storage.SessionStore(config.SESSION_DIR)


@router.get("", response_model=list[SessionListItem])
def list_sessions():
    items = []
    for s in store.list_sessions():
        items.append(SessionListItem(
            id=s["id"],
            name=s.get("name") or s.get("filename") or s["id"],
            filename=s.get("filename", ""),
            status=s["status"],
            duration_sec=s.get("duration_sec"),
            created_at=s.get("created_at", ""),
        ))
    return items
