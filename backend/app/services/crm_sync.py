"""
Sincroniza contacts_crm desde las tablas fuente de hotboat-whatsapp (solo lectura,
misma Postgres compartida) y calcula reservation_score.

No toca `contacts` ni `sync_contacts()` (app/services/sync_hotboat.py) — reutiliza
únicamente su helper `_source_engine()` para conectarse a las tablas de origen.

Fuentes:
  - whatsapp_leads         -> cubre leads que nunca reservaron (atribucion, ultimo contacto)
  - all_appointments       -> cubre historial de reservas (veces_hotboat, ticket_medio, extras)
  - whatsapp_carts         -> señal de carrito activo para el score
  - tracked_link_conversion -> embudo web (vio precios / eligio fecha) para leads a los que
                               el bot les mando un link de seguimiento (tracked_quote_links)
  - contacts (local)       -> solo para resolver linked_contact_id por email (lectura)
"""
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import text
from sqlmodel import Session, select

from app.database import engine as local_engine
from app.models.contact_crm import ContactCRM
from app.services.sync_hotboat import _source_engine

logger = logging.getLogger(__name__)

# Pesos ajustables del score 0-100. Cada regla suma como maximo una vez.
SCORE_WEIGHTS = {
    "veces_hotboat": 25,        # cliente recurrente, señal mas fuerte
    "lead_status_active": 15,   # lead clasificado como potencial/cliente en whatsapp_leads
    "ad_source_present": 10,    # llego por un anuncio (self-selected intent)
    "recent_contact_3d": 20,    # ultimo contacto hace <=3 dias
    "recent_contact_14d": 10,   # ultimo contacto hace <=14 dias
    "stale_30d_penalty": -15,   # ultimo contacto hace >30 dias
    "active_cart": 20,          # tiene un carrito de WhatsApp activo (ultimos 7 dias)
    "link_clicked": 15,         # hizo click en el link de cotizacion que le mando el bot
    "link_selected_date": 15,   # y llego a elegir fecha en el calendario (muy cerca de reservar)
}

# Orden de avance del funnel web (booking_visitor_summary.classification), de menos a mas
# interes — usado solo para derivar los flags legacy link_viewed_prices/link_selected_date
# a partir de la clasificacion real. Debe reflejar el mismo orden que _classify_visitor()
# en hotboat-whatsapp/app/booking/router.py.
_WEB_CLASSIFICATION_RANK = [
    "👀 Solo mirando",
    "🔍 Explorando",
    "🔍 Explorando activamente",
    "⭐ Muy interesado",
    "🎯 Listo para reservar",
    "✅ Reservó",
]


def _web_rank(classification: str | None) -> int:
    try:
        return _WEB_CLASSIFICATION_RANK.index(classification or "")
    except ValueError:
        return -1


def _normalize_phone_e164(raw: str | None, default_country: str = "+56") -> str | None:
    """Misma logica que app/utils/phone.py de hotboat-whatsapp (duplicada a proposito:
    evita un import cross-repo fragil por un par de reglas simples)."""
    if not raw:
        return None
    digits = re.sub(r"[^\d+]", "", str(raw))
    if not digits:
        return None
    if digits.startswith("+"):
        return digits
    if len(digits) == 9 and digits.startswith("9"):
        return f"{default_country}{digits}"
    if default_country == "+56" and len(digits) == 11 and digits.startswith("56"):
        return f"+{digits}"
    return digits

ACTIVE_LEAD_STATUSES = {"potential_client", "customer"}


def _naive_utcnow() -> datetime:
    return datetime.utcnow()


def _days_since(ts, now: datetime) -> int | None:
    if not ts:
        return None
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return (now - ts).days


def _compute_score(d: dict, has_active_cart: bool, now: datetime) -> tuple[int, dict]:
    score = 0
    breakdown: dict[str, int] = {}

    if (d.get("veces_hotboat") or 0) >= 1:
        w = SCORE_WEIGHTS["veces_hotboat"]
        score += w
        breakdown["veces_hotboat"] = w

    if d.get("lead_status") in ACTIVE_LEAD_STATUSES:
        w = SCORE_WEIGHTS["lead_status_active"]
        score += w
        breakdown["lead_status_active"] = w

    if d.get("ad_source"):
        w = SCORE_WEIGHTS["ad_source_present"]
        score += w
        breakdown["ad_source_present"] = w

    days = _days_since(d.get("last_interaction_at"), now)
    if days is not None:
        if days <= 3:
            w = SCORE_WEIGHTS["recent_contact_3d"]
            score += w
            breakdown["recent_contact_3d"] = w
        elif days <= 14:
            w = SCORE_WEIGHTS["recent_contact_14d"]
            score += w
            breakdown["recent_contact_14d"] = w
        elif days > 30:
            w = SCORE_WEIGHTS["stale_30d_penalty"]
            score += w
            breakdown["stale_30d_penalty"] = w

    if has_active_cart:
        w = SCORE_WEIGHTS["active_cart"]
        score += w
        breakdown["active_cart"] = w

    if d.get("link_clicked"):
        w = SCORE_WEIGHTS["link_clicked"]
        score += w
        breakdown["link_clicked"] = w

    if d.get("link_selected_date"):
        w = SCORE_WEIGHTS["link_selected_date"]
        score += w
        breakdown["link_selected_date"] = w

    score = max(0, min(100, score))
    return score, breakdown


def run() -> dict:
    engine = _source_engine()
    now = _naive_utcnow()
    merged: dict[str, dict] = {}

    with engine.connect() as conn:
        leads = conn.execute(text("""
            SELECT phone_number, customer_name, lead_status, ad_source, ad_platform,
                   ad_creative_url, last_interaction_at
            FROM whatsapp_leads
            WHERE phone_number IS NOT NULL AND phone_number <> ''
        """)).fetchall()

        bookings = conn.execute(text("""
            SELECT telefono AS phone, MAX(email) AS email, MAX(nombre_cliente) AS name,
                   COUNT(*) AS veces_hotboat, MAX(fecha) AS ultima_visita,
                   ROUND(AVG(ingreso_total)::numeric, 0) AS ticket_medio,
                   MAX(NULLIF(utm_campaign, '')) AS utm_campaign,
                   MAX(como_supieron) AS como_supieron
            FROM all_appointments
            WHERE telefono IS NOT NULL AND telefono <> ''
              AND status NOT IN ('cancelled', 'no_show', 'pending')
            GROUP BY telefono
        """)).fetchall()

        extras_by_phone: dict[str, list[str]] = {}
        for r in conn.execute(text("""
            SELECT telefono, array_agg(DISTINCT key) AS extras
            FROM all_appointments,
                 jsonb_object_keys(extras_json) AS key
            WHERE telefono IS NOT NULL AND telefono <> ''
              AND extras_json IS NOT NULL AND extras_json::text <> '{}'
              AND jsonb_typeof(extras_json) = 'object'
              AND key NOT LIKE 'aloj__%%'
            GROUP BY telefono
        """)).fetchall():
            extras_by_phone[r[0]] = [s for s in (r[1] or []) if s]

        active_cart_phones = {
            r[0] for r in conn.execute(text("""
                SELECT DISTINCT phone_number FROM whatsapp_carts
                WHERE cart_data IS NOT NULL AND cart_data::text <> '[]'
                  AND updated_at > NOW() - INTERVAL '7 days'
            """)).fetchall()
        }

        try:
            link_conversions = conn.execute(text("""
                SELECT phone, click_count, viewed_prices, selected_date, last_seen_at
                FROM tracked_link_conversion
                WHERE phone IS NOT NULL AND phone <> ''
            """)).fetchall()
        except Exception:
            # Vista puede no existir aun en algunos entornos (feature reciente) — no bloquear el sync.
            link_conversions = []

        try:
            # Resumen precalculado por hotboat-whatsapp (booking_visitor_summary): una fila
            # por telefono, ya con la clasificacion real del funnel (no solo 3 flags booleanos)
            # y agregada sobre todo el recorrido — mucho mas liviano que el JOIN en vivo de antes.
            direct_web_conversions = conn.execute(text("""
                SELECT phone, visitor_id, session_count, event_count,
                       first_seen_at, last_seen_at, classification, classification_desc
                FROM booking_visitor_summary
                WHERE phone IS NOT NULL AND phone <> ''
            """)).fetchall()
        except Exception:
            # Tabla nueva — puede no existir aun en algunos entornos (falta correr el deploy
            # de hotboat-whatsapp con ensure_db_columns()).
            direct_web_conversions = []

    for row in leads:
        phone = row.phone_number
        if not phone:
            continue
        d = merged.setdefault(phone, {})
        if row.customer_name:
            d["name"] = row.customer_name
        d["lead_status"] = row.lead_status
        d["ad_source"] = row.ad_source
        d["ad_platform"] = row.ad_platform
        d["ad_creative_url"] = row.ad_creative_url
        d["last_interaction_at"] = row.last_interaction_at

    for row in bookings:
        phone = row.phone
        if not phone:
            continue
        d = merged.setdefault(phone, {})
        if row.email:
            d["email"] = row.email.strip().lower()
        if row.name and not d.get("name"):
            d["name"] = row.name
        d["veces_hotboat"] = int(row.veces_hotboat or 0)
        d["ultima_visita"] = row.ultima_visita
        d["ticket_medio"] = float(row.ticket_medio) if row.ticket_medio is not None else None
        d["extras_favoritos"] = extras_by_phone.get(phone)
        if not d.get("ad_source"):
            d["ad_source"] = row.utm_campaign or row.como_supieron

    for row in link_conversions:
        phone = _normalize_phone_e164(row.phone)
        if not phone:
            continue
        d = merged.setdefault(phone, {})
        d["link_clicked"] = bool(row.click_count and row.click_count > 0)
        d["link_viewed_prices"] = bool(row.viewed_prices)
        d["link_selected_date"] = bool(row.selected_date)
        d["link_last_seen_at"] = row.last_seen_at

    for row in direct_web_conversions:
        phone = _normalize_phone_e164(row.phone)
        if not phone:
            continue
        d = merged.setdefault(phone, {})
        d["link_clicked"] = True
        d["link_viewed_prices"] = bool(d.get("link_viewed_prices")) or _web_rank(row.classification) >= _web_rank("🔍 Explorando")
        d["link_selected_date"] = bool(d.get("link_selected_date")) or _web_rank(row.classification) >= _web_rank("⭐ Muy interesado")
        existing_seen = d.get("link_last_seen_at")
        if not existing_seen or (row.last_seen_at and row.last_seen_at > existing_seen):
            d["link_last_seen_at"] = row.last_seen_at

        d["web_classification"] = row.classification
        d["web_classification_desc"] = row.classification_desc
        d["web_last_seen_at"] = row.last_seen_at
        d["web_session_count"] = row.session_count

    created = updated = 0
    with Session(local_engine) as session:
        # Bulk-fetch once instead of one round-trip per contact (N+1 was the same
        # anti-pattern that made the phone backfill script slow against Railway).
        existing_by_phone = {
            c.phone: c for c in session.exec(select(ContactCRM)).all() if c.phone
        }
        contact_id_by_email = {
            row[1].lower(): row[0]
            for row in session.execute(text("SELECT id, email FROM contacts WHERE email IS NOT NULL")).all()
        }

        for phone, d in merged.items():
            has_cart = phone in active_cart_phones
            score, breakdown = _compute_score(d, has_cart, now)

            email = d.get("email")
            linked_id = contact_id_by_email.get(email) if email else None

            existing = existing_by_phone.get(phone)
            if existing:
                existing.name = d.get("name") or existing.name
                existing.email = email or existing.email
                existing.linked_contact_id = linked_id
                existing.ad_source = d.get("ad_source") or existing.ad_source
                existing.ad_platform = d.get("ad_platform") or existing.ad_platform
                existing.ad_creative_url = d.get("ad_creative_url") or existing.ad_creative_url
                existing.lead_status = d.get("lead_status") or existing.lead_status
                existing.last_interaction_at = d.get("last_interaction_at") or existing.last_interaction_at
                existing.veces_hotboat = d.get("veces_hotboat", existing.veces_hotboat)
                existing.ultima_visita = d.get("ultima_visita") or existing.ultima_visita
                existing.ticket_medio = d.get("ticket_medio") if d.get("ticket_medio") is not None else existing.ticket_medio
                existing.extras_favoritos = d.get("extras_favoritos") or existing.extras_favoritos
                existing.link_clicked = d.get("link_clicked", existing.link_clicked)
                existing.link_viewed_prices = d.get("link_viewed_prices", existing.link_viewed_prices)
                existing.link_selected_date = d.get("link_selected_date", existing.link_selected_date)
                existing.link_last_seen_at = d.get("link_last_seen_at") or existing.link_last_seen_at
                existing.web_classification = d.get("web_classification") or existing.web_classification
                existing.web_classification_desc = d.get("web_classification_desc") or existing.web_classification_desc
                existing.web_last_seen_at = d.get("web_last_seen_at") or existing.web_last_seen_at
                existing.web_session_count = d.get("web_session_count", existing.web_session_count)
                existing.reservation_score = score
                existing.score_updated_at = now
                existing.score_breakdown = breakdown
                existing.updated_at = now
                session.add(existing)
                updated += 1
            else:
                session.add(ContactCRM(
                    phone=phone,
                    email=email,
                    name=d.get("name"),
                    linked_contact_id=linked_id,
                    ad_source=d.get("ad_source"),
                    ad_platform=d.get("ad_platform"),
                    ad_creative_url=d.get("ad_creative_url"),
                    lead_status=d.get("lead_status"),
                    last_interaction_at=d.get("last_interaction_at"),
                    veces_hotboat=d.get("veces_hotboat", 0),
                    ultima_visita=d.get("ultima_visita"),
                    ticket_medio=d.get("ticket_medio"),
                    extras_favoritos=d.get("extras_favoritos"),
                    link_clicked=d.get("link_clicked", False),
                    link_viewed_prices=d.get("link_viewed_prices", False),
                    link_selected_date=d.get("link_selected_date", False),
                    link_last_seen_at=d.get("link_last_seen_at"),
                    web_classification=d.get("web_classification"),
                    web_classification_desc=d.get("web_classification_desc"),
                    web_last_seen_at=d.get("web_last_seen_at"),
                    web_session_count=d.get("web_session_count", 0),
                    reservation_score=score,
                    score_updated_at=now,
                    score_breakdown=breakdown,
                ))
                created += 1

        session.commit()

    result = {"created": created, "updated": updated, "total": len(merged)}
    logger.info("crm_sync completado: %s", result)
    return result
