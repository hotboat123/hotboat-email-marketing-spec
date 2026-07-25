"""
Tráfico de la página web (landing hotboat.cl + sitio de reservas), día a día.

Fuente: booking_visitor_events en la base de HotBoat (HOTBOAT_DATABASE_URL /
mismo motor que sync_hotboat.py) — tabla compartida entre hotboat-marketing-web
(landing) y hotboat-whatsapp (booking-soft.html), distinguibles solo por qué
event_type aparece en cada sesión (ver EVENTOS DE CADA SITIO abajo). Los
"pagos" confirmados salen de all_appointments (misma base), ya que un evento
de tracking nunca puede confirmar por sí solo que un pago realmente se hizo.

Definiciones acordadas con el dueño del negocio (2026-07-24):
- "Sesión útil" (no rebote) = tiene al menos un evento aparte de los
  eventos AUTOMÁTICOS que no reflejan ninguna acción real del visitante:
  page_visit/page_visit_booking (se disparan solos al cargar la página) y
  exit/page_left (se disparan solos al cerrar/cambiar de pestaña, vía
  sendBeacon en visibilitychange — ver tracker.js y booking-soft.html
  _trackLeave()). Corregido 2026-07-25: la versión original solo excluía
  page_visit(_booking), así que una sesión que solo abrió y cerró la
  pestaña (0 interacción real) contaba como "útil" porque el beacon de
  salida técnicamente "es un evento" — eso hacía que la tasa de rebote
  real (68%) se viera como 8%. Cualquier otra interacción sigue contando,
  sin importar cuán mínima sea.
- "% que llenaron el pop-up" = form_submissions (cualquier signup_form) del
  día, como % de las sesiones totales de ese día. No hay session_id en
  form_submissions, así que esto es una tasa agregada, no un funnel por
  sesión individual.
- "% que llenaron WhatsApp" = evento click_whatsapp (solo se dispara en la
  landing) — cuenta a quien hizo click para abrir WhatsApp, no a quien
  efectivamente escribió algo ahí.
"""
from datetime import date, timedelta
from typing import Optional
from sqlalchemy import create_engine, text
from app.core.config import settings

# Eventos que se disparan SOLOS (carga de página, cierre de pestaña) y no
# reflejan ninguna acción real del visitante — no cuentan como
# "interacción" para la definición de sesión útil.
_ENTRY_EVENTS = ("page_visit", "page_visit_booking", "exit", "page_left")


def _source_engine():
    """Mismo patrón que sync_hotboat.py — conecta a la base de HotBoat
    (booking_visitor_events, all_appointments viven ahí, no en esta app)."""
    url = settings.HOTBOAT_DATABASE_URL or settings.DATABASE_URL
    return create_engine(url)


def get_web_traffic_daily(desde: date, hasta: date) -> dict:
    engine = _source_engine()
    hasta_excl = hasta + timedelta(days=1)  # rango inclusivo del lado del cliente

    with engine.connect() as conn:
        # Sesiones totales + útiles por día. Un CTE agrupa cada sesión a su
        # primer día visto y si tuvo alguna interacción real, luego se cuenta
        # por día — evita contar dos veces una sesión que cruzó medianoche.
        sessions_rows = conn.execute(text("""
            WITH session_days AS (
                SELECT
                    session_id,
                    MIN(DATE(recorded_at AT TIME ZONE 'America/Santiago')) AS day,
                    BOOL_OR(event_type NOT IN :entry_events) AS interacted
                FROM booking_visitor_events
                WHERE recorded_at >= :desde AND recorded_at < :hasta_excl
                GROUP BY session_id
            )
            SELECT day, COUNT(*) AS total, COUNT(*) FILTER (WHERE interacted) AS useful
            FROM session_days
            GROUP BY day ORDER BY day
        """), {"entry_events": _ENTRY_EVENTS, "desde": desde, "hasta_excl": hasta_excl}).fetchall()

        # Eventos puntuales por día (cada uno cuenta sesiones DISTINTAS con
        # ese evento ese día, no el total de disparos — dos clicks en el
        # mismo botón en la misma sesión cuentan una vez).
        event_rows = conn.execute(text("""
            SELECT
                DATE(recorded_at AT TIME ZONE 'America/Santiago') AS day,
                event_type,
                COUNT(DISTINCT session_id) AS n
            FROM booking_visitor_events
            WHERE recorded_at >= :desde AND recorded_at < :hasta_excl
              AND event_type IN ('click_whatsapp', 'click_reservar', 'view_precio', 'view_prices', 'date_selected', 'booking_completed')
            GROUP BY day, event_type
        """), {"desde": desde, "hasta_excl": hasta_excl}).fetchall()

        # "Vio precio y se fue" — sesiones con view_precio/view_prices que
        # NUNCA llegaron a date_selected en esa misma sesión.
        price_left_rows = conn.execute(text("""
            WITH price_sessions AS (
                SELECT
                    session_id,
                    MIN(DATE(recorded_at AT TIME ZONE 'America/Santiago')) AS day,
                    BOOL_OR(event_type = 'date_selected') AS advanced
                FROM booking_visitor_events
                WHERE recorded_at >= :desde AND recorded_at < :hasta_excl
                  AND session_id IN (
                      SELECT session_id FROM booking_visitor_events
                      WHERE event_type IN ('view_precio', 'view_prices')
                        AND recorded_at >= :desde AND recorded_at < :hasta_excl
                  )
                GROUP BY session_id
            )
            SELECT day, COUNT(*) FILTER (WHERE NOT advanced) AS left_after_price, COUNT(*) AS saw_price
            FROM price_sessions GROUP BY day ORDER BY day
        """), {"desde": desde, "hasta_excl": hasta_excl}).fetchall()

        # Pagos confirmados — payment_status es la única fuente que
        # realmente prueba que se pagó, un evento de tracking no alcanza.
        paid_rows = conn.execute(text("""
            SELECT DATE(COALESCE(updated_at, created_at) AT TIME ZONE 'America/Santiago') AS day, COUNT(*) AS n
            FROM all_appointments
            WHERE payment_status IN ('approved', 'completed')
              AND COALESCE(updated_at, created_at) >= :desde AND COALESCE(updated_at, created_at) < :hasta_excl
            GROUP BY day ORDER BY day
        """), {"desde": desde, "hasta_excl": hasta_excl}).fetchall()

    # Ensamblar por día — arranca de un dict con todos los días del rango en
    # cero, así el front no tiene que rellenar huecos.
    by_day: dict = {}
    d = desde
    while d <= hasta:
        by_day[d.isoformat()] = {
            "day": d.isoformat(),
            "total_sessions": 0, "useful_sessions": 0,
            "whatsapp_clicks": 0, "went_to_booking": 0,
            "viewed_price": 0, "selected_date": 0, "booking_completed_events": 0,
            "viewed_price_left": 0, "paid": 0,
            "popup_fills": 0,
        }
        d += timedelta(days=1)

    for day, total, useful in sessions_rows:
        key = day.isoformat()
        if key in by_day:
            by_day[key]["total_sessions"] = total
            by_day[key]["useful_sessions"] = useful

    for day, event_type, n in event_rows:
        key = day.isoformat()
        if key not in by_day:
            continue
        if event_type == "click_whatsapp":
            by_day[key]["whatsapp_clicks"] = n
        elif event_type == "click_reservar":
            by_day[key]["went_to_booking"] = n
        elif event_type in ("view_precio", "view_prices"):
            by_day[key]["viewed_price"] += n
        elif event_type == "date_selected":
            by_day[key]["selected_date"] = n
        elif event_type == "booking_completed":
            by_day[key]["booking_completed_events"] = n

    for day, left_after_price, saw_price in price_left_rows:
        key = day.isoformat()
        if key in by_day:
            by_day[key]["viewed_price_left"] = left_after_price

    for day, n in paid_rows:
        key = day.isoformat()
        if key in by_day:
            by_day[key]["paid"] = n

    popup_by_day = _popup_fills_by_day(desde, hasta_excl)
    for key, n in popup_by_day.items():
        if key in by_day:
            by_day[key]["popup_fills"] = n

    daily = []
    for row in by_day.values():
        useful = row["useful_sessions"]
        total = row["total_sessions"]
        row["conversion_rate"] = round(row["paid"] / useful * 100, 2) if useful else 0.0
        row["found_expensive_rate"] = round(row["viewed_price_left"] / row["viewed_price"] * 100, 1) if row["viewed_price"] else 0.0
        row["popup_fill_rate"] = round(row["popup_fills"] / total * 100, 1) if total else 0.0
        row["whatsapp_click_rate"] = round(row["whatsapp_clicks"] / total * 100, 1) if total else 0.0
        row["went_to_booking_rate"] = round(row["went_to_booking"] / total * 100, 1) if total else 0.0
        daily.append(row)

    totals = _sum_totals(daily)
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "daily": daily, "totals": totals}


def _popup_fills_by_day(desde: date, hasta_excl: date) -> dict:
    """form_submissions vive en ESTA app (no en la base de HotBoat) — sesión
    normal de SQLModel contra el engine local, no el engine cruzado."""
    from sqlmodel import Session, select, func as sqlfunc
    from app.database import engine as _local_engine
    from app.models.form import FormSubmission

    result: dict = {}
    with Session(_local_engine) as session:
        rows = session.exec(
            select(
                sqlfunc.date(FormSubmission.created_at).label("day"),
                sqlfunc.count(FormSubmission.id),
            )
            .where(FormSubmission.created_at >= desde, FormSubmission.created_at < hasta_excl)
            .group_by(sqlfunc.date(FormSubmission.created_at))
        ).all()
        for day, n in rows:
            key = day.isoformat() if hasattr(day, "isoformat") else str(day)
            result[key] = n
    return result


def _sum_totals(daily: list[dict]) -> dict:
    total_sessions = sum(r["total_sessions"] for r in daily)
    useful_sessions = sum(r["useful_sessions"] for r in daily)
    whatsapp_clicks = sum(r["whatsapp_clicks"] for r in daily)
    went_to_booking = sum(r["went_to_booking"] for r in daily)
    viewed_price = sum(r["viewed_price"] for r in daily)
    viewed_price_left = sum(r["viewed_price_left"] for r in daily)
    selected_date = sum(r["selected_date"] for r in daily)
    paid = sum(r["paid"] for r in daily)
    popup_fills = sum(r["popup_fills"] for r in daily)
    return {
        "total_sessions": total_sessions,
        "useful_sessions": useful_sessions,
        "bounce_rate": round((1 - useful_sessions / total_sessions) * 100, 1) if total_sessions else 0.0,
        "popup_fills": popup_fills,
        "popup_fill_rate": round(popup_fills / total_sessions * 100, 1) if total_sessions else 0.0,
        "whatsapp_clicks": whatsapp_clicks,
        "whatsapp_click_rate": round(whatsapp_clicks / total_sessions * 100, 1) if total_sessions else 0.0,
        "went_to_booking": went_to_booking,
        "went_to_booking_rate": round(went_to_booking / total_sessions * 100, 1) if total_sessions else 0.0,
        "viewed_price": viewed_price,
        "viewed_price_left": viewed_price_left,
        "found_expensive_rate": round(viewed_price_left / viewed_price * 100, 1) if viewed_price else 0.0,
        "selected_date": selected_date,
        "paid": paid,
        "conversion_rate": round(paid / useful_sessions * 100, 2) if useful_sessions else 0.0,
    }
