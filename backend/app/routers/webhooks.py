import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlmodel import Session, select
from app.database import get_session
from app.core.config import settings
from app.models.campaign import CampaignSend
from app.models.automation import AutomationRun

logger = logging.getLogger(__name__)
router = APIRouter()

STATUS_MAP = {
    "email.sent":       "sent",
    "email.delivered":  "delivered",
    "email.opened":     "opened",
    "email.clicked":    "clicked",
    "email.bounced":    "bounced",
    "email.complained": "complained",
}


def _verify_svix(payload: bytes, svix_id: str, svix_timestamp: str, svix_signature: str) -> bool:
    """Verifica la firma Svix que usa Resend para sus webhooks."""
    secret = settings.RESEND_WEBHOOK_SECRET
    if not secret:
        return True

    # El secret de Resend/Svix empieza con "whsec_" — hay que decodificar el resto en base64
    if secret.startswith("whsec_"):
        secret = secret[6:]
    try:
        secret_bytes = base64.b64decode(secret)
    except Exception:
        return False

    # Contenido firmado: "{svix-id}.{svix-timestamp}.{body}"
    signed = f"{svix_id}.{svix_timestamp}.".encode() + payload

    expected = base64.b64encode(
        hmac.new(secret_bytes, signed, hashlib.sha256).digest()
    ).decode()

    # svix-signature puede contener varias firmas separadas por espacio: "v1,abc123 v1,xyz..."
    for sig in svix_signature.split(" "):
        if sig.startswith("v1,"):
            if hmac.compare_digest(expected, sig[3:]):
                return True
    return False


@router.post("/resend")
async def resend_webhook(
    request: Request,
    svix_id: str = Header(default="", alias="svix-id"),
    svix_timestamp: str = Header(default="", alias="svix-timestamp"),
    svix_signature: str = Header(default="", alias="svix-signature"),
    session: Session = Depends(get_session),
):
    body = await request.body()

    if not _verify_svix(body, svix_id, svix_timestamp, svix_signature):
        logger.warning("Webhook con firma Svix inválida — rechazado")
        raise HTTPException(status_code=401, detail="Firma inválida")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido")

    event_type = event.get("type", "")
    data = event.get("data", {})
    resend_id = data.get("email_id") or data.get("id")

    logger.info("Webhook recibido: type=%s resend_id=%s", event_type, resend_id)

    new_status = STATUS_MAP.get(event_type)
    if not new_status or not resend_id:
        return {"ok": True}

    # Un resend_id puede pertenecer a un envío de campaña O de automatización
    # (Cumpleaños, Carrito abandonado, etc.) — se prueban ambas tablas, cada
    # una tiene sus propias columnas status/opened_at/clicked_at.
    record = session.exec(select(CampaignSend).where(CampaignSend.resend_id == resend_id)).first()
    record_label = "CampaignSend"
    if not record:
        record = session.exec(select(AutomationRun).where(AutomationRun.resend_id == resend_id)).first()
        record_label = "AutomationRun"
    if not record:
        logger.warning("Ningún CampaignSend/AutomationRun encontrado para resend_id=%s", resend_id)
        return {"ok": True}

    # CampaignSend.status IS the Resend event vocabulary (queued/sent/
    # delivered/opened/clicked/bounced/complained) — overwriting it here is
    # existing, correct behavior. AutomationRun.status means something
    # narrower (sent/failed/skipped — whether the automation itself fired
    # successfully) and is set once at send time; overwriting it with e.g.
    # "opened" would break the sent/failed counts elsewhere, so only the
    # timestamp columns below get touched for that table.
    if record_label == "CampaignSend":
        record.status = new_status
    now = datetime.utcnow()
    if new_status == "delivered":
        record.delivered_at = now
    elif new_status == "opened" and not record.opened_at:
        record.opened_at = now
    elif new_status == "clicked" and not record.clicked_at:
        record.clicked_at = now
    elif new_status == "bounced":
        record.bounced_at = now

    session.add(record)
    session.commit()
    logger.info("%s actualizado: id=%s status=%s", record_label, record.id, new_status)
    return {"ok": True}
