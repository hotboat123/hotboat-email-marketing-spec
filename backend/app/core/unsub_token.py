import hmac
import hashlib
import base64
from urllib.parse import quote
from app.core.config import settings


def make_unsub_token(email: str) -> str:
    key = settings.SECRET_KEY.encode()
    msg = email.lower().encode()
    sig = hmac.new(key, msg, digestmod=hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def verify_unsub_token(email: str, token: str) -> bool:
    try:
        return hmac.compare_digest(make_unsub_token(email), token)
    except Exception:
        return False


def unsub_url(email: str) -> str:
    token = make_unsub_token(email)
    return f"{settings.FRONTEND_URL}/unsubscribe?email={quote(email)}&token={token}"
