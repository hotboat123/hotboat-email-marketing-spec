"""Best-effort ad attribution parsing from a landing-page URL.

Popup-form submissions store the raw page URL the visitor was on
(Contact.origin_utm) — e.g. "https://hotboat.cl/?fbclid=IwZX...". That's
rarely useful to read directly, so this derives a clean {ad_source,
utm_campaign, utm_medium} from it wherever possible.

Important limitation: fbclid alone (no utm_campaign/utm_content) can't be
resolved to a specific ad — Meta doesn't expose a "look up which ad this
click belongs to" API to advertisers. Ads without UTM parameters configured
on their destination link only ever produce a generic "Meta ad" label, not
the actual ad/campaign name. Fix that upstream (Ads Manager URL params), not
by trying to decode fbclid.
"""
from typing import Optional
from urllib.parse import urlparse, parse_qs

_UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_id", "fbclid")

_PLATFORM_LABELS = {
    "ig": "Instagram",
    "instagram": "Instagram",
    "fb": "Facebook",
    "facebook": "Facebook",
    "google": "Google",
    "tiktok": "TikTok",
}


def _extract_query_params(url: str) -> dict:
    """Handles the normal case (?utm_source=ig&fbclid=...) and a messier one
    seen in real data: a second URL embedded un-encoded in the query string
    (?https://wa.hotboat.cl/booking?utm_campaign=X&...), which parse_qs
    returns as a single garbled key ending in "...?utm_campaign" — still
    recoverable by matching the key's suffix."""
    if not url:
        return {}
    try:
        query = urlparse(url).query
        parsed = parse_qs(query)
    except Exception:
        return {}
    out = {}
    for key, values in parsed.items():
        if not values:
            continue
        clean_key = key.rsplit("?", 1)[-1]
        if clean_key in _UTM_KEYS and clean_key not in out:
            out[clean_key] = values[0]
    return out


def parse_ad_attribution(url: Optional[str]) -> dict:
    """Returns {ad_source, utm_campaign, utm_medium}, all None when nothing
    is resolvable (organic/direct visit)."""
    params = _extract_query_params(url or "")
    utm_campaign = params.get("utm_campaign")
    utm_medium = params.get("utm_medium")
    utm_source = params.get("utm_source")
    fbclid = params.get("fbclid")

    if utm_campaign:
        ad_source = utm_campaign.replace("-", " ").replace("_", " ").strip()
    elif fbclid:
        platform = _PLATFORM_LABELS.get((utm_source or "").lower(), "Meta (Facebook/Instagram)")
        ad_source = f"Anuncio de {platform} — sin datos de campaña"
    elif utm_source:
        ad_source = utm_source
    else:
        ad_source = None

    return {"ad_source": ad_source, "utm_campaign": utm_campaign, "utm_medium": utm_medium}
