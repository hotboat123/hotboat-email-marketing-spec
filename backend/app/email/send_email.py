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

# Triggers whose call site already writes its own CampaignSend/AutomationRun
# row (with html_content — see those call sites) for richer per-contact
# tracking (open/click/bounce). Logging those again here would double-list
# them on "Correos enviados". Everything else — unsubscribe notices, internal
# admin alerts, and any FUTURE call site that forgets to add its own tracking
# row — gets written to EmailLog unconditionally below, so the log can never
# silently miss a real send again.
_TRACKED_ELSEWHERE = {"campaign_send", "campaign_test_send", "manual_referral"}


def _already_tracked(trigger: str) -> bool:
    return trigger in _TRACKED_ELSEWHERE or trigger.startswith("automation_")


def _log_untracked_send(
    *, to, subject: str, html: str, provider: Optional[str],
    message_id: Optional[str], sent: bool, error: Optional[str], trigger: str,
) -> None:
    try:
        from sqlmodel import Session
        from app.database import engine
        from app.models.email_log import EmailLog

        to_str = ", ".join(to) if isinstance(to, list) else to
        with Session(engine) as session:
            session.add(EmailLog(
                to_email=to_str, subject=subject, html_content=html,
                provider=provider, message_id=message_id, sent=sent,
                error=error, trigger=trigger,
            ))
            session.commit()
    except Exception:
        # Logging the send must never be why the send itself fails/looks failed.
        logger.exception("EmailLog write failed for trigger=%s", trigger)


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
        if not _already_tracked(trigger):
            _log_untracked_send(
                to=real_to, subject=subject, html=html, provider=provider,
                message_id=message_id, sent=True, error=None, trigger=trigger,
            )
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
        if not _already_tracked(trigger):
            _log_untracked_send(
                to=real_to, subject=subject, html=html, provider=provider,
                message_id=None, sent=False, error=error_detail, trigger=trigger,
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
