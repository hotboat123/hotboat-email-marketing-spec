from fastapi import APIRouter, BackgroundTasks, Depends
from sqlmodel import Session
from app.database import get_session
from app.core.deps import require_admin
from app.models.user import User
from app.services.sync_hotboat import sync_contacts

router = APIRouter()

_last_result: dict = {}


@router.post("/run")
def run_sync(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Dispara la sincronización de contactos desde HotBoat en background."""
    global _last_result
    _last_result = {"status": "running"}
    background_tasks.add_task(_do_sync, session)
    return {"status": "started"}


@router.get("/status")
def sync_status(_: User = Depends(require_admin)):
    return _last_result


def _do_sync(session: Session):
    global _last_result
    try:
        result = sync_contacts(session)
        _last_result = {"status": "done", **result}
    except Exception as exc:
        _last_result = {"status": "error", "detail": str(exc)}
