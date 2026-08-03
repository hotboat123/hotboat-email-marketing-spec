"""Send email via Resend. Thin wrapper — one dedicated call site so
app.email.send_email can be the only place that decides which provider runs."""
import logging
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def send_resend_email(
    to: Union[str, List[str]],
    subject: str,
    html: str,
    from_address: str,
    api_key: str,
    *,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    tags: Optional[Dict[str, str]] = None,
) -> dict:
    """Returns Resend's response dict, or raises on failure."""
    import resend

    if not api_key:
        raise ValueError("RESEND_API_KEY is not configured")

    resend.api_key = api_key
    payload = {
        "from": from_address,
        "to": to if isinstance(to, list) else [to],
        "subject": subject,
        "html": html,
    }
    if bcc:
        payload["bcc"] = bcc
    if reply_to:
        payload["reply_to"] = [reply_to]
    if headers:
        payload["headers"] = headers
    if tags:
        payload["tags"] = [{"name": k, "value": v} for k, v in tags.items()]

    result = resend.Emails.send(payload)
    logger.info("Resend email sent to %s id=%s", to, result.get("id", "?"))
    return result
