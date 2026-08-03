"""Send email via AWS SES (sesv2 client), always as raw MIME.

Unlike the sibling hotboat-whatsapp migration (which used
Content={"Simple": ...} since no call site needed custom headers), this repo
actively uses List-Unsubscribe/List-Unsubscribe-Post (CAN-SPAM one-click
unsubscribe) and Resend tags on every campaign/automation send today — SES's
simple Content API doesn't support either, so raw MIME is the only path here,
used unconditionally (including the two tag-less internal admin notices) so
there's a single send code path to reason about, not two.
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from functools import lru_cache
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@lru_cache()
def _get_client(access_key: str, secret_key: str, region: str):
    import boto3
    return boto3.client(
        "sesv2",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def _safe_from_header(from_address: str) -> str:
    """
    Encode ONLY the display-name portion of a 'Name <addr>' string, leaving
    the email address bare — handing the raw string to a MIME encoder
    RFC-2047-encodes the whole thing (name + address) when the name has
    non-ASCII characters, and SES then rejects the result with "Missing
    final '@domain'". (Same fix as the sibling hotboat-whatsapp migration.)
    """
    name, addr = parseaddr(from_address)
    if not addr:
        return from_address
    return formataddr((name, addr))


def _build_raw_mime(
    from_address: str,
    to: Union[str, List[str]],
    subject: str,
    html: str,
    *,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> bytes:
    msg = MIMEMultipart("alternative")
    msg["From"] = _safe_from_header(from_address)
    msg["To"] = ", ".join(to) if isinstance(to, list) else to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    for key, value in (headers or {}).items():
        msg[key] = value
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg.as_bytes()


def send_ses_email(
    to: Union[str, List[str]],
    subject: str,
    html: str,
    from_address: str,
    access_key: str,
    secret_key: str,
    region: str,
    configuration_set: str = "",
    *,
    bcc: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    tags: Optional[Dict[str, str]] = None,
) -> dict:
    """Returns the SES sesv2 send_email response dict, or raises on failure."""
    if not access_key or not secret_key:
        raise ValueError("AWS SES credentials are not configured")

    client = _get_client(access_key, secret_key, region)
    mime_bytes = _build_raw_mime(
        from_address, to, subject, html, bcc=bcc, reply_to=reply_to, headers=headers,
    )

    destination = {"ToAddresses": to if isinstance(to, list) else [to]}
    if bcc:
        destination["BccAddresses"] = bcc

    kwargs = dict(
        Destination=destination,
        Content={"Raw": {"Data": mime_bytes}},
    )
    if configuration_set:
        kwargs["ConfigurationSetName"] = configuration_set
    if tags:
        kwargs["EmailTags"] = [{"Name": k, "Value": v} for k, v in tags.items()]

    result = client.send_email(**kwargs)
    logger.info("SES email sent to %s id=%s", to, result.get("MessageId", "?"))
    return result
