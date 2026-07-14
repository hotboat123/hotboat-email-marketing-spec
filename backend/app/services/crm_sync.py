"""
Sincroniza contacts_crm desde las tablas fuente de hotboat-whatsapp (solo lectura,
misma Postgres compartida) y calcula reservation_score.

No toca `contacts` ni `sync_contacts()` (app/services/sync_hotboat.py) — reutiliza
únicamente su helper `_source_engine()` para conectarse a las tablas de origen.

Fuentes:
  - whatsapp_leads         -> cubre leads que nunca reservaron (atribucion, ultimo contacto)
  - all_appointments       -> cubre historial de reservas (veces_hotboat, ticket_medio, extras)
  - whatsapp_carts         -> señal de extras agregados al carrito para el score
  - tracked_link_conversion -> embudo web (vio precios / eligio fecha / clicks) para leads a
                               los que el bot les mando un link de seguimiento (tracked_quote_links)
  - booking_visitor_summary -> cantidad de eventos (clicks/paginas) en la navegacion web directa
  - contacts (local)       -> solo para resolver linked_contact_id por email (lectura)
"""
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import text
from sqlmodel import Session, select

from app.database import engine as local_engine
from app.models.contact_crm import ContactCRM
from app.models.score_weight import ScoreWeight
from app.services.sync_hotboat import _source_engine

logger = logging.getLogger(__name__)

# Pesos por defecto del score 0-100 (usados para sembrar la tabla score_weights la
# primera vez, y como fallback si esa tabla esta vacia). Cada regla suma como maximo
# una vez. Los puntos reales que usa run() se leen de score_weights — editables desde
# el dashboard (Llamadas > Configuración) sin tocar código, ver _load_weights().
SCORE_WEIGHTS = {
    "veces_hotboat": 25,        # cliente recurrente, señal mas fuerte
    "lead_status_active": 15,   # lead clasificado como potencial/cliente en whatsapp_leads
    "recent_contact_3d": 20,    # ultimo contacto hace <=3 dias
    "recent_contact_14d": 10,   # ultimo contacto hace <=14 dias
    "stale_30d_penalty": -15,   # ultimo contacto hace >30 dias
    "link_clicked": 15,         # hizo click en el link de cotizacion que le mando el bot
    "link_selected_date": 15,   # y llego a elegir fecha en el calendario (muy cerca de reservar)
    "engagement_high": 20,      # 10+ clicks/eventos en el sistema de reservas o la pagina web
    "engagement_mid": 12,       # 4-9 clicks/eventos
    "engagement_low": 6,        # 1-3 clicks/eventos
    "cart_has_extras": 10,      # agrego algun extra (no solo la reserva base) al carrito de WhatsApp
    "clicked_pay": 15,          # llego a apretar el boton "Pagar" en booking-soft.html (aunque no haya pagado)
}

SCORE_WEIGHT_LABELS = {
    "veces_hotboat": "Ya reservó y pagó antes",
    "lead_status_active": "Lead activo en whatsapp_leads",
    "recent_contact_3d": "Contacto en los últimos 3 días",
    "recent_contact_14d": "Contacto entre 4 y 14 días atrás",
    "stale_30d_penalty": "Sin contacto hace más de 30 días",
    "link_clicked": "Hizo clic en el link que le mandó el bot",
    "link_selected_date": "Llegó a elegir fecha en el calendario",
    "clicked_pay": "Hizo clic en \"Pagar\" (aunque no haya pagado)",
    "engagement_high": "10+ clicks en el sistema de reservas o la web",
    "engagement_mid": "4-9 clicks en el sistema de reservas o la web",
    "engagement_low": "1-3 clicks en el sistema de reservas o la web",
    "cart_has_extras": "Agregó extras al carrito de WhatsApp",
}

# Umbrales de clicks/eventos (suma de link_click_count + web_event_count) para
# "engagement_*" — entre mas interactuo con el sistema de reservas y la web, mas cerca esta.
_ENGAGEMENT_HIGH_MIN = 10
_ENGAGEMENT_MID_MIN = 4


def _load_weights(session: Session) -> dict[str, int]:
    """Puntos reales a usar en este sync: lo que haya en score_weights, completado
    con los defaults de SCORE_WEIGHTS para cualquier clave que todavia no exista ahi
    (ej. una regla nueva agregada al código antes de que alguien la edite en el dashboard)."""
    rows = session.exec(select(ScoreWeight)).all()
    weights = {r.key: r.points for r in rows}
    for key, default in SCORE_WEIGHTS.items():
        weights.setdefault(key, default)
    return weights

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
    # Any other digit-only number (foreign country code already included, just
    # missing the '+') — every phone-format duplicate found in contacts_crm was
    # exactly this: the same number stored once with '+' and once without.
    return f"+{digits}"

ACTIVE_LEAD_STATUSES = {"potential_client", "customer"}


def _naive_utcnow() -> datetime:
    return datetime.utcnow()


def _days_since(ts, now: datetime) -> int | None:
    if not ts:
        return None
    if ts.tzinfo is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return (now - ts).days


def _compute_score(d: dict, has_cart_extras: bool, has_clicked_pay: bool, weights: dict[str, int], now: datetime) -> tuple[int, dict]:
    score = 0
    breakdown: dict[str, int] = {}

    if (d.get("veces_hotboat") or 0) >= 1:
        w = weights["veces_hotboat"]
        score += w
        breakdown["veces_hotboat"] = w

    if d.get("lead_status") in ACTIVE_LEAD_STATUSES:
        w = weights["lead_status_active"]
        score += w
        breakdown["lead_status_active"] = w

    days = _days_since(d.get("last_interaction_at"), now)
    if days is not None:
        if days <= 3:
            w = weights["recent_contact_3d"]
            score += w
            breakdown["recent_contact_3d"] = w
        elif days <= 14:
            w = weights["recent_contact_14d"]
            score += w
            breakdown["recent_contact_14d"] = w
        elif days > 30:
            w = weights["stale_30d_penalty"]
            score += w
            breakdown["stale_30d_penalty"] = w

    if d.get("link_clicked"):
        w = weights["link_clicked"]
        score += w
        breakdown["link_clicked"] = w

    if d.get("link_selected_date"):
        w = weights["link_selected_date"]
        score += w
        breakdown["link_selected_date"] = w

    clicks = (d.get("link_click_count") or 0) + (d.get("web_event_count") or 0)
    if clicks >= _ENGAGEMENT_HIGH_MIN:
        w = weights["engagement_high"]
        score += w
        breakdown["engagement_high"] = w
    elif clicks >= _ENGAGEMENT_MID_MIN:
        w = weights["engagement_mid"]
        score += w
        breakdown["engagement_mid"] = w
    elif clicks >= 1:
        w = weights["engagement_low"]
        score += w
        breakdown["engagement_low"] = w

    if has_cart_extras:
        w = weights["cart_has_extras"]
        score += w
        breakdown["cart_has_extras"] = w

    if has_clicked_pay:
        w = weights["clicked_pay"]
        score += w
        breakdown["clicked_pay"] = w

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
              AND status NOT IN ('cancelled', 'no_show', 'pending', 'pending_payment')
            GROUP BY telefono
        """)).fetchall()

        # Reservas web que todavia estan esperando pago (dentro de la ventana de
        # 120 min antes del auto-cleanup en hotboat-whatsapp/app/main.py) — antes
        # se contaban como "pago" en veces_hotboat de arriba porque el filtro
        # excluia el status 'pending' que nunca se usa, no 'pending_payment' que
        # es el real.
        pending_bookings = conn.execute(text("""
            SELECT telefono AS phone, COUNT(*) AS veces_pendiente
            FROM all_appointments
            WHERE telefono IS NOT NULL AND telefono <> ''
              AND source = 'hotboat_web'
              AND status = 'pending_payment'
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
            norm_phone = _normalize_phone_e164(r[0])
            if norm_phone:
                extras_by_phone[norm_phone] = [s for s in (r[1] or []) if s]

        cart_extras_phones = {
            _normalize_phone_e164(r[0]) for r in conn.execute(text("""
                SELECT DISTINCT phone_number FROM whatsapp_carts
                WHERE cart_data IS NOT NULL AND cart_data::text <> '[]'
                  AND updated_at > NOW() - INTERVAL '7 days'
                  AND EXISTS (
                    SELECT 1 FROM jsonb_array_elements(cart_data::jsonb) elem
                    WHERE elem->>'item_type' = 'extra'
                  )
            """)).fetchall()
        } - {None}

        try:
            # Cubre a cualquiera que llego a apretar "Pagar" en booking-soft.html — tanto
            # via link de WhatsApp (link_token -> tracked_quote_links) como navegacion
            # directa (session_id/visitor_id -> booking_visitor_identity), igual que el
            # UNION de get_crm_web_activity en este mismo repo.
            clicked_pay_phones = {
                _normalize_phone_e164(r[0]) for r in conn.execute(text("""
                    SELECT DISTINCT bvi.phone
                    FROM booking_visitor_events bve
                    JOIN booking_visitor_identity bvi
                      ON bve.session_id = bvi.session_id
                         OR (bvi.visitor_id IS NOT NULL AND bve.visitor_id = bvi.visitor_id)
                    WHERE bve.event_type = 'click_pagar' AND bvi.phone IS NOT NULL AND bvi.phone <> ''
                    UNION
                    SELECT DISTINCT tql.phone
                    FROM booking_visitor_events bve
                    JOIN tracked_quote_links tql ON bve.link_token = tql.token
                    WHERE bve.event_type = 'click_pagar' AND tql.phone IS NOT NULL AND tql.phone <> ''
                """)).fetchall()
            } - {None}
        except Exception:
            clicked_pay_phones = set()

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
        phone = _normalize_phone_e164(row.phone_number)
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
        phone = _normalize_phone_e164(row.phone)
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

    for row in pending_bookings:
        phone = _normalize_phone_e164(row.phone)
        if not phone:
            continue
        d = merged.setdefault(phone, {})
        d["veces_pendiente"] = int(row.veces_pendiente or 0)

    for row in link_conversions:
        phone = _normalize_phone_e164(row.phone)
        if not phone:
            continue
        d = merged.setdefault(phone, {})
        # Un mismo telefono puede tener mas de un token en tracked_quote_links (el bot
        # genera uno nuevo cada vez que reenvia el link) — la vista trae una fila por
        # token, asi que hay que combinarlas en vez de pisar: el link viejo sin clicks
        # no debe borrar la señal del link nuevo que si se clickeo.
        d["link_clicked"] = bool(d.get("link_clicked")) or bool(row.click_count and row.click_count > 0)
        d["link_viewed_prices"] = bool(d.get("link_viewed_prices")) or bool(row.viewed_prices)
        d["link_selected_date"] = bool(d.get("link_selected_date")) or bool(row.selected_date)
        existing_link_seen = d.get("link_last_seen_at")
        if not existing_link_seen or (row.last_seen_at and row.last_seen_at > existing_link_seen):
            d["link_last_seen_at"] = row.last_seen_at
        d["link_click_count"] = int(d.get("link_click_count") or 0) + int(row.click_count or 0)
        d["channel_whatsapp_link"] = True

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
        d["channel_direct_web"] = True
        d["web_session_count"] = row.session_count
        d["web_event_count"] = int(row.event_count or 0)

    created = updated = 0
    with Session(local_engine) as session:
        weights = _load_weights(session)

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
            has_extras = phone in cart_extras_phones
            has_clicked_pay = phone in clicked_pay_phones
            score, breakdown = _compute_score(d, has_extras, has_clicked_pay, weights, now)

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
                # A diferencia de veces_hotboat (arriba), esto SI se resetea a 0 cada
                # corrida si el telefono no aparece en pending_bookings — una reserva
                # pendiente vive como mucho 120 min (auto-cleanup), asi que "no aparece"
                # significa que ya se pago o se borro, no que hay que preservar el valor viejo.
                existing.veces_pendiente = d.get("veces_pendiente", 0)
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
                existing.channel_whatsapp_link = existing.channel_whatsapp_link or d.get("channel_whatsapp_link", False)
                existing.channel_direct_web = existing.channel_direct_web or d.get("channel_direct_web", False)
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
                    veces_pendiente=d.get("veces_pendiente", 0),
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
                    channel_whatsapp_link=d.get("channel_whatsapp_link", False),
                    channel_direct_web=d.get("channel_direct_web", False),
                    reservation_score=score,
                    score_updated_at=now,
                    score_breakdown=breakdown,
                ))
                created += 1

        session.commit()

    result = {"created": created, "updated": updated, "total": len(merged)}
    logger.info("crm_sync completado: %s", result)
    return result
