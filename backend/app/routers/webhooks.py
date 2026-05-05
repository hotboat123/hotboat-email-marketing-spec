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


def _verify_signature(payload: bytes, signature: str) -> bool:
    if not settings.RESEND_WEBHOOK_SECRET:
        return True
    expected = hmac.new(
        settings.RESEND_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/resend")
async def resend_webhook(
    request: Request,
    resend_signature: str = Header(default="", alias="resend-signature"),
    session: Session = Depends(get_session),
):
    body = await request.body()
    if not _verify_signature(body, resend_signature):
        raise HTTPException(status_code=401, detail="Firma inválida")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido")

    event_type = event.get("type", "")
    data = event.get("data", {})
    resend_id = data.get("email_id") or data.get("id")

    new_status = STATUS_MAP.get(event_type)
    if not new_status or not resend_id:
        return {"ok": True}

    send = session.exec(select(CampaignSend).where(CampaignSend.resend_id == resend_id)).first()
    if not send:
        logger.warning("CampaignSend no encontrado para resend_id=%s", resend_id)
        return {"ok": True}

    send.status = new_status
    now = datetime.utcnow()
    if new_status == "delivered":
        send.delivered_at = now
    elif new_status == "opened" and not send.opened_at:
        send.opened_at = now
    elif new_status == "clicked" and not send.clicked_at:
        send.clicked_at = now
    elif new_status == "bounced":
        send.bounced_at = now

    session.add(send)
    session.commit()
    return {"ok": True}
