from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.database import get_session
from app.core.deps import require_admin
from app.models.user import User
from app.services.sync_hotboat import sync_contacts

router = APIRouter()


@router.post("/run")
def run_sync(
    session: Session = Depends(get_session),
    _: User = Depends(require_admin),
):
    """Sincroniza contactos desde HotBoat de forma síncrona y devuelve el resultado."""
    try:
        result = sync_contacts(session)
        return {"status": "done", **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
def sync_status(_: User = Depends(require_admin)):
    return {"status": "idle"}
