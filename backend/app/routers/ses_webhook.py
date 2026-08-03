"""
AWS SES delivery events, pushed via SNS to an HTTPS endpoint (SES has no
direct HTTP webhooks like Resend — everything goes through SNS). Replaces
`webhooks.py`'s `/resend` (Svix-signed) endpoint for whichever traffic is on
SES — `webhooks.py` stays live and unchanged for as long as any traffic is
still on Resend during the gradual cutover.

Every message is signature-verified before being acted on:

- Cert host allowlist: the signing certificate is only ever fetched if
  SigningCertURL's host matches sns.<region>.amazonaws.com over https,
  checked strictly before any network call — otherwise an attacker could
  point SigningCertURL at their own host and get us to "verify" a signature
  against a certificate they control (SSRF / signature spoofing).
- Signature: RSA-PKCS1v15 over AWS's canonical string-to-sign (SHA1 for
  SignatureVersion "1", SHA256 for "2").

SubscriptionConfirmation's SubscribeURL is only ever logged, never fetched —
that confirmation is a one-time step done by hand, in a browser, when the
SNS topic is first wired up; auto-fetching it would be a second, needless
SSRF surface for something that only happens once.

Notification events update the SAME two tables `webhooks.py` already
updates (CampaignSend, AutomationRun) — same lookup order (CampaignSend
first, then AutomationRun, by the `resend_id` column, which now also holds
SES message ids — see the migration plan for why that column isn't renamed)
and the same AutomationRun.status protection (never overwritten by delivery
vocabulary, only its timestamp columns are).
"""
import base64
import json
import logging
import re
import urllib.request
from datetime import datetime
from functools import lru_cache
from urllib.parse import urlparse

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.database import get_session
from app.models.automation import AutomationRun
from app.models.campaign import CampaignSend

logger = logging.getLogger(__name__)
router = APIRouter()

_SNS_CERT_HOST_RE = re.compile(r"^sns\.[a-zA-Z0-9-]+\.amazonaws\.com$")

_NOTIFICATION_FIELDS = ["Message", "MessageId", "Subject", "Timestamp", "TopicArn", "Type"]
_SUBSCRIPTION_FIELDS = ["Message", "MessageId", "SubscribeURL", "Timestamp", "Token", "TopicArn", "Type"]

# SES/SNS eventType -> same status vocabulary webhooks.py's STATUS_MAP already
# uses for Resend, so nothing downstream (analytics, UI) needs to change.
SES_STATUS_MAP = {
    "Delivery": "delivered",
    "Open": "opened",
    "Click": "clicked",
    "Bounce": "bounced",
    "Complaint": "complained",
}


def _is_allowed_cert_host(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme != "https":
        return False
    return bool(parsed.hostname and _SNS_CERT_HOST_RE.match(parsed.hostname))


@lru_cache(maxsize=8)
def _fetch_signing_cert(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 — host already allowlisted by caller
        return resp.read()


def _build_string_to_sign(message: dict) -> bytes:
    msg_type = message.get("Type", "")
    if msg_type == "Notification":
        fields = _NOTIFICATION_FIELDS
    elif msg_type in ("SubscriptionConfirmation", "UnsubscribeConfirmation"):
        fields = _SUBSCRIPTION_FIELDS
    else:
        raise ValueError(f"Cannot build string-to-sign for message type: {msg_type!r}")

    parts = []
    for key in fields:
        if key in message:
            parts.append(key)
            parts.append(str(message[key]))
    return ("\n".join(parts) + "\n").encode("utf-8")


def _verify_sns_signature(message: dict) -> bool:
    cert_url = message.get("SigningCertURL", "")
    if not _is_allowed_cert_host(cert_url):
        logger.error("SES webhook: rejected SigningCertURL host: %s", cert_url)
        return False

    try:
        cert_bytes = _fetch_signing_cert(cert_url)
        public_key = x509.load_pem_x509_certificate(cert_bytes, default_backend()).public_key()
        signature = base64.b64decode(message.get("Signature", ""))
        string_to_sign = _build_string_to_sign(message)
        algo = hashes.SHA256() if str(message.get("SignatureVersion")) == "2" else hashes.SHA1()
        public_key.verify(signature, string_to_sign, padding.PKCS1v15(), algo)
        return True
    except InvalidSignature:
        logger.error("SES webhook: invalid SNS signature (TopicArn=%s)", message.get("TopicArn"))
        return False
    except Exception as e:
        logger.error("SES webhook: signature verification error: %s", e)
        return False


@router.post("/ses")
async def ses_events(request: Request, session: Session = Depends(get_session)):
    raw = await request.body()
    try:
        envelope = json.loads(raw)
    except Exception:
        logger.error("SES webhook: unparseable body: %s", raw[:500])
        return {"ok": False}

    if not _verify_sns_signature(envelope):
        raise HTTPException(status_code=400, detail="invalid SNS signature")

    msg_type = request.headers.get("x-amz-sns-message-type") or envelope.get("Type", "")

    if msg_type == "SubscriptionConfirmation":
        subscribe_url = envelope.get("SubscribeURL", "")
        logger.warning(
            "SES/SNS SubscriptionConfirmation received for TopicArn=%s — "
            "visit this URL manually in a browser to confirm it (NOT auto-fetched, "
            "to avoid an SSRF risk): %s",
            envelope.get("TopicArn"), subscribe_url,
        )
        return {"ok": True, "action": "manual_confirmation_required"}

    if msg_type == "UnsubscribeConfirmation":
        logger.warning("SES/SNS UnsubscribeConfirmation received: TopicArn=%s", envelope.get("TopicArn"))
        return {"ok": True}

    if msg_type == "Notification":
        try:
            message = json.loads(envelope.get("Message", "{}"))
        except Exception:
            logger.error("SES webhook: Notification with unparseable inner Message")
            return {"ok": False}
        _handle_ses_event(message, session)
        return {"ok": True}

    logger.warning("SES webhook: unrecognized message type: %s", msg_type)
    return {"ok": True}


def _handle_ses_event(message: dict, session: Session) -> None:
    event_type = message.get("eventType") or message.get("notificationType") or ""
    mail = message.get("mail", {}) or {}
    ses_message_id = mail.get("messageId")

    new_status = SES_STATUS_MAP.get(event_type)
    if not new_status or not ses_message_id:
        logger.info("SES event received: eventType=%s message_id=%s (no-op)", event_type or "unknown", ses_message_id)
        return

    # Same dual-table lookup as webhooks.py's Resend consumer — a message id
    # can belong to a campaign send OR a lifecycle-automation send.
    record = session.exec(select(CampaignSend).where(CampaignSend.resend_id == ses_message_id)).first()
    record_label = "CampaignSend"
    if not record:
        record = session.exec(select(AutomationRun).where(AutomationRun.resend_id == ses_message_id)).first()
        record_label = "AutomationRun"
    if not record:
        logger.warning("No CampaignSend/AutomationRun found for ses_message_id=%s", ses_message_id)
        return

    # Same protection as webhooks.py: CampaignSend.status IS the delivery
    # vocabulary and gets overwritten; AutomationRun.status means something
    # narrower (sent/failed/skipped) and is never touched here — only its
    # timestamp columns are.
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
    logger.info("%s updated via SES: id=%s status=%s", record_label, record.id, new_status)
