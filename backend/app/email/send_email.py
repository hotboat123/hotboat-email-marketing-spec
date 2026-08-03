"""
Single funnel for all outgoing mail — campaigns, automations, and internal
admin notices alike. Every call site should import `send_email` from here
instead of calling a provider (Resend, SES) directly, so a global provider
flip (`settings.EMAIL_PROVIDER`) and the `EMAIL_OVERRIDE_TO` safety valve
apply everywhere at once.
"""
import logging
from typing import Any, Dict, List, Optional, Union

from app.core.config import settings as _settings

logger = logging.getLogger(__name__)


def default_from_address() -> str:
    """The from-address for whichever provider is currently active — one
    place call sites ask instead of repeating the same ternary 9 times."""
    provider = (_settings.EMAIL_PROVIDER or "resend").strip().lower()
    return _settings.SES_FROM_EMAIL if provider == "ses" else _settings.RESEND_FROM_EMAIL


def send_email(
    to: Union[str, List[str]],
    subject: str,
    html: str,
    from_address: str,
    *,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    tags: Optional[Dict[str, str]] = None,
    trigger: str = "unspecified",
) -> Dict[str, Any]:
    """
    Returns {"sent": bool, "reason": str, "provider": str, "message_id": str|None}.
    Never raises — callers keep their existing "check the result" pattern.

    `trigger` is a free-text label for logging only (e.g. "campaign_send",
    "automation_birthday") — no routing effect today, but a hook for a
    future per-trigger provider filter without touching call sites again.
    """
    if not _settings.EMAIL_ENABLED:
        return {"sent": False, "reason": "email_disabled", "provider": None, "message_id": None}

    # EMAIL_OVERRIDE_TO — enforced here, first, before provider selection, so
    # no call site (including a full campaign batch loop) can ever bypass it.
    # Redirects both `to` and `bcc`: a real bcc leaking real contact data
    # during a staging test is exactly the risk this flag exists to prevent.
    override = (_settings.EMAIL_OVERRIDE_TO or "").strip()
    real_to, real_bcc = to, bcc
    if override:
        logger.warning(
            "EMAIL_OVERRIDE_TO active: redirecting mail (trigger=%s, real_to=%s, real_bcc=%s) -> %s",
            trigger, real_to, real_bcc, override,
        )
        to = override
        bcc = None
        subject = f"[OVERRIDE was: {real_to}] {subject}"

    provider = (_settings.EMAIL_PROVIDER or "resend").strip().lower()

    try:
        if provider == "ses":
            result = _send_via_ses(
                to=to, subject=subject, html=html, from_address=from_address,
                bcc=bcc, reply_to=reply_to, headers=headers, tags=tags,
            )
            message_id = result.get("MessageId")
        else:
            result = _send_via_resend(
                to=to, subject=subject, html=html, from_address=from_address,
                bcc=bcc, reply_to=reply_to, headers=headers, tags=tags,
            )
            message_id = result.get("id") if isinstance(result, dict) else None
        return {"sent": True, "reason": "ok", "provider": provider, "message_id": message_id}
    except Exception as e:
        error_detail = str(e)
        resp = getattr(e, "response", None)
        if isinstance(resp, dict) and "Error" in resp:
            # botocore.exceptions.ClientError (SES)
            error_detail += f" | ses_code={resp['Error'].get('Code')} ses_message={resp['Error'].get('Message')}"
        elif resp is not None:
            # Resend's ResendError — response is not a plain dict
            error_detail += f" | response: {resp}"
        if hasattr(e, "body"):
            error_detail += f" | body: {e.body}"
        logger.error(
            "Email send FAILED provider=%s trigger=%s to=%s from=%s | %s",
            provider, trigger, to, from_address, error_detail,
        )
        return {"sent": False, "reason": error_detail, "provider": provider, "message_id": None}


def _send_via_resend(*, to, subject, html, from_address, bcc, reply_to, headers, tags):
    from app.email.resend_provider import send_resend_email

    return send_resend_email(
        to=to, subject=subject, html=html, from_address=from_address,
        api_key=_settings.RESEND_API_KEY,
        bcc=bcc, reply_to=reply_to, headers=headers, tags=tags,
    )


def _send_via_ses(*, to, subject, html, from_address, bcc, reply_to, headers, tags):
    from app.email.ses_provider import send_ses_email

    return send_ses_email(
        to=to, subject=subject, html=html, from_address=from_address,
        access_key=_settings.AWS_ACCESS_KEY_ID,
        secret_key=_settings.AWS_SECRET_ACCESS_KEY,
        region=_settings.AWS_REGION,
        configuration_set=_settings.SES_CONFIGURATION_SET,
        bcc=bcc, reply_to=reply_to, headers=headers, tags=tags,
    )
