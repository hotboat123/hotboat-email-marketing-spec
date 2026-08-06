"""
Comparación por origen de tráfico (Google / Meta / Otro) — pestaña "Fuentes".
Responde "¿dónde conviene invertir?": conversión y, donde hay dato real de
gasto (solo Meta), costo por reserva.

Mismo motor/tablas que web_traffic_analytics.py / whatsapp_traffic_analytics.py
(booking_visitor_events, all_appointments, whatsapp_conversations) más
contacts_crm/meta_ads_insights — todo en la misma Postgres compartida (ver
ads.py, que ya hace exactamente este mismo cruce contacts_crm↔all_appointments
vía _source_engine()).

Bucketing a "meta"/"google"/"otro": ver platform_attribution.py — sesiones
anónimas usan SESSION_PLATFORM_BUCKET_SQL (utm/referrer), teléfonos ya
identificados (reservas, conversaciones) usan CC_PLATFORM_BUCKET_SQL
(contacts_crm.platform, ya calculado por crm_sync.py).

Dos números de "reservas" para Meta que NO calzan entre sí, a propósito:
- bookings (en get_platform_comparison): cruce amplio por teléfono vía
  contacts_crm.platform — cualquier reserva pagada de un teléfono clasificado
  como Meta, tenga o no un anuncio identificado.
- meta_bookings_matched (denominador de cost_per_booking): el subconjunto que
  además matcheó un nombre real de anuncio de Meta (mismo criterio que la
  pestaña Anuncios, vía ads.py::_bookings_by_level_id reusado tal cual — NO
  _bookings_by_ad_name directo, que incluye cualquier contacts_crm.ad_source
  no nulo, incluyendo fuentes que no son de Meta) — así el costo-por-reserva
  sigue calzando con lo que ya muestra esa pestaña.
Google y Otro: spend/cost_per_booking siempre None, nunca un número inventado
(no existe ninguna integración de Google Ads en ningún repo).
"""
from datetime import date, timedelta

from sqlalchemy import text

from app.services.web_traffic_analytics import _source_engine, PHONE_FLUJO_LATERAL, _USEFUL_SESSION_SECONDS
from app.services.whatsapp_traffic_analytics import _USEFUL_MIN_INCOMING
from app.services.platform_attribution import SESSION_PLATFORM_BUCKET_SQL, CC_PLATFORM_BUCKET_SQL
from app.routers.ads import _bookings_by_level_id

_BUCKETS = ("meta", "google", "otro")

_PAID_CRITERIA = """(
    (a.pagos IS NOT NULL AND jsonb_array_length(a.pagos) > 0)
    OR a.payment_status IN ('approved', 'completed')
)"""


def _empty_bucket(platform: str) -> dict:
    return {
        "platform": platform,
        "web_sessions": 0, "web_useful_sessions": 0,
        "whatsapp_conversations": 0, "whatsapp_useful_conversations": 0,
        "bookings": 0,
        "conversion_rate": 0.0,
        "spend": None, "cost_per_booking": None,
        "meta_bookings_matched": None,
    }


def get_platform_comparison(desde: date, hasta: date) -> dict:
    engine = _source_engine()
    hasta_excl = hasta + timedelta(days=1)

    by_bucket = {p: _empty_bucket(p) for p in _BUCKETS}

    with engine.connect() as conn:
        # Sesiones web (mismo criterio de "útil" >5s y misma exclusión de
        # sesiones que llegaron por un link del bot que web_traffic_analytics.py,
        # para que web_sessions acá sea consistente con esa pestaña).
        session_rows = conn.execute(text(f"""
            WITH session_platform AS (
                SELECT
                    session_id,
                    {SESSION_PLATFORM_BUCKET_SQL} AS platform,
                    EXTRACT(EPOCH FROM (MAX(recorded_at) - MIN(recorded_at))) > :useful_seconds AS interacted
                FROM booking_visitor_events
                WHERE recorded_at >= :desde AND recorded_at < :hasta_excl
                  AND session_id NOT IN (
                      SELECT session_id FROM booking_visitor_events
                      WHERE link_token IS NOT NULL
                        AND recorded_at >= :desde AND recorded_at < :hasta_excl
                  )
                GROUP BY session_id, {SESSION_PLATFORM_BUCKET_SQL}
            )
            SELECT platform, COUNT(*) AS total, COUNT(*) FILTER (WHERE interacted) AS useful
            FROM session_platform GROUP BY platform
        """), {"desde": desde, "hasta_excl": hasta_excl, "useful_seconds": _USEFUL_SESSION_SECONDS}).fetchall()
        for platform, total, useful in session_rows:
            if platform in by_bucket:
                by_bucket[platform]["web_sessions"] = total
                by_bucket[platform]["web_useful_sessions"] = useful

        # Conversaciones de WhatsApp — mismo cohorte (primer mensaje del rango)
        # y mismo umbral "útil" (>=2 entrantes) que whatsapp_traffic_analytics.py.
        wa_rows = conn.execute(text(f"""
            WITH conv AS (
                SELECT
                    phone_number,
                    COUNT(*) FILTER (WHERE direction = 'incoming') AS n_incoming
                FROM whatsapp_conversations
                WHERE created_at >= :desde AND created_at < :hasta_excl
                GROUP BY phone_number
            )
            SELECT {CC_PLATFORM_BUCKET_SQL} AS platform,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE c.n_incoming >= :useful_min) AS useful
            FROM conv c
            LEFT JOIN contacts_crm cc
              ON regexp_replace(cc.phone, '[^0-9]', '', 'g') = c.phone_number
            GROUP BY platform
        """), {"desde": desde, "hasta_excl": hasta_excl, "useful_min": _USEFUL_MIN_INCOMING}).fetchall()
        for platform, total, useful in wa_rows:
            if platform in by_bucket:
                by_bucket[platform]["whatsapp_conversations"] = total
                by_bucket[platform]["whatsapp_useful_conversations"] = useful

        # Reservas pagadas — cruce amplio por teléfono (contacts_crm.platform),
        # sin filtrar por flujo: acá se quiere el total real por plataforma,
        # no evitar doble conteo entre pestañas Web/WhatsApp (ver docstring).
        booking_rows = conn.execute(text(f"""
            SELECT {CC_PLATFORM_BUCKET_SQL} AS platform, COUNT(*) AS n
            FROM all_appointments a
            LEFT JOIN contacts_crm cc
              ON regexp_replace(cc.phone, '[^0-9]', '', 'g') = regexp_replace(a.telefono, '[^0-9]', '', 'g')
            WHERE {_PAID_CRITERIA}
              AND DATE(a.created_at AT TIME ZONE 'America/Santiago') >= :desde
              AND DATE(a.created_at AT TIME ZONE 'America/Santiago') <= :hasta
            GROUP BY platform
        """), {"desde": desde, "hasta": hasta}).fetchall()
        for platform, n in booking_rows:
            if platform in by_bucket:
                by_bucket[platform]["bookings"] = n

        # Gasto real + reservas con anuncio identificado — SOLO Meta. Reusa
        # tal cual el join por nombre de anuncio que ya usa la pestaña
        # Anuncios, para que cost_per_booking calce con lo que esa pestaña
        # ya muestra.
        try:
            spend_row = conn.execute(text("""
                SELECT SUM(i.spend) AS spend
                FROM meta_ads_insights i
                WHERE i.date_start >= :desde AND i.date_start <= :hasta
            """), {"desde": desde, "hasta": hasta}).first()
            meta_spend = float(spend_row.spend) if spend_row and spend_row.spend is not None else None

            # _bookings_by_level_id (no _bookings_by_ad_name directo) — ese
            # otro devuelve TODO contacts_crm.ad_source no nulo (incluye
            # "boca a boca", "tripadvisor", literal "google", etc., que no
            # son anuncios de Meta); _bookings_by_level_id es lo que cruza
            # contra meta_ads.name real y es lo que la pestaña Anuncios
            # efectivamente suma como "reservas" — verificado 2026-08-06 que
            # sin este filtro meta_bookings_matched salía en 31 (más que las
            # 19 "bookings" de todo el bucket Meta, un contrasentido), y con
            # el filtro correcto da 9, calzando con /ads/summary?level=ad.
            bookings_by_ad_id = _bookings_by_level_id(conn, "ad", desde.isoformat(), hasta.isoformat())
            meta_bookings_matched = sum(bookings_by_ad_id.values()) if bookings_by_ad_id else 0

            by_bucket["meta"]["spend"] = round(meta_spend) if meta_spend is not None else None
            by_bucket["meta"]["meta_bookings_matched"] = meta_bookings_matched
            by_bucket["meta"]["cost_per_booking"] = (
                round(meta_spend / meta_bookings_matched, 1)
                if meta_spend is not None and meta_bookings_matched else None
            )
        except Exception:
            # meta_ads_insights puede no existir en algunos entornos — no
            # bloquear el resto de la comparación por eso.
            pass

    for row in by_bucket.values():
        base = row["web_useful_sessions"] + row["whatsapp_useful_conversations"]
        row["conversion_rate"] = round(row["bookings"] / base * 100, 2) if base else 0.0

    return {
        "desde": desde.isoformat(), "hasta": hasta.isoformat(),
        "rows": [by_bucket[p] for p in _BUCKETS],
    }


def get_flujo_platform_crosstab(desde: date, hasta: date) -> list[dict]:
    """Tabla cruzada flujo (1/2/3) x plataforma (meta/google/otro) — 9 celdas,
    para ver ej. qué % de las reservas de Meta pasaron por WhatsApp. Reusa
    PHONE_FLUJO_LATERAL sin modificarlo (mismo criterio de clasificación que
    las pestañas Web/WhatsApp)."""
    engine = _source_engine()

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT
                pf.flujo,
                {CC_PLATFORM_BUCKET_SQL} AS platform,
                COUNT(*) AS total
            FROM all_appointments a
            {PHONE_FLUJO_LATERAL}
            LEFT JOIN contacts_crm cc
              ON regexp_replace(cc.phone, '[^0-9]', '', 'g') = regexp_replace(a.telefono, '[^0-9]', '', 'g')
            WHERE {_PAID_CRITERIA}
              AND DATE(a.created_at AT TIME ZONE 'America/Santiago') >= :desde
              AND DATE(a.created_at AT TIME ZONE 'America/Santiago') <= :hasta
            GROUP BY pf.flujo, platform
        """), {"desde": desde, "hasta": hasta}).fetchall()

    by_cell = {(f, p): 0 for f in ("flujo_1", "flujo_2", "flujo_3") for p in _BUCKETS}
    for flujo, platform, total in rows:
        if (flujo, platform) in by_cell:
            by_cell[(flujo, platform)] = total

    total_paid = sum(by_cell.values()) or 1
    return [
        {"flujo": f, "platform": p, "paid": n, "share_of_total_pct": round(n / total_paid * 100, 1)}
        for (f, p), n in by_cell.items()
    ]
