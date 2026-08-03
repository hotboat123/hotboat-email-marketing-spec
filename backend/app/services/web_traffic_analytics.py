"""
Tráfico de la página web (landing hotboat.cl + sitio de reservas), día a día.

Fuente: booking_visitor_events en la base de HotBoat (HOTBOAT_DATABASE_URL /
mismo motor que sync_hotboat.py) — tabla compartida entre hotboat-marketing-web
(landing) y hotboat-whatsapp (booking-soft.html), distinguibles solo por qué
event_type aparece en cada sesión (ver EVENTOS DE CADA SITIO abajo). Los
"pagos" confirmados salen de all_appointments (misma base), ya que un evento
de tracking nunca puede confirmar por sí solo que un pago realmente se hizo.

Definiciones acordadas con el dueño del negocio:
- "Sesión útil" (no rebote) = duró MÁS DE 5 SEGUNDOS, medido entre el primer
  y el último evento de la sesión (incluye el beacon automático de salida
  exit/page_left, que sí marca correctamente cuándo se fue — ver
  tracker.js/booking-soft.html _trackLeave()). Cambiado 2026-07-25 de una
  definición basada en tipo de evento (¿hubo algún evento que no fuera
  page_visit/exit?) a una basada en duración, a pedido del dueño tras ver
  el histograma de distribución: con 60 días de datos, ~38% de las
  sesiones duran 3 segundos o menos (rebote real, gente que abre y se va
  casi de inmediato) y la tasa de interacción recién empieza a subir en
  serio pasado ese punto — 5s es el corte elegido.
- "% que llenaron el pop-up" = form_submissions (cualquier signup_form) del
  día, como % de las sesiones totales de ese día. No hay session_id en
  form_submissions, así que esto es una tasa agregada, no un funnel por
  sesión individual.
- "% que llenaron WhatsApp" = evento click_whatsapp (solo se dispara en la
  landing) — cuenta a quien hizo click para abrir WhatsApp, no a quien
  efectivamente escribió algo ahí.

Clasificación de tráfico (agregado 2026-08-03, corrige doble conteo entre
esta pestaña y la de WhatsApp): booking_visitor_events no distingue el
origen de una sesión con una columna propia, pero cuando el bot de
WhatsApp le manda a un lead un link de reserva (tracked_quote_links), TODA
la sesión de booking-soft.html que resulta de abrir ese link queda marcada
con link_token IS NOT NULL (ver visitor_tracking.py en hotboat-whatsapp).
Antes, esas sesiones se contaban acá como "web" Y en la pestaña WhatsApp
por teléfono — la misma persona aparecía dos veces. Ahora se excluyen de
TODAS las consultas de esta página: "sesión web" pasa a significar
específicamente "sesión que nunca llegó por un link que mandó el bot".

Esto separa limpio el Flujo 1 (WhatsApp puro) del Flujo 2 (web puro). El
Flujo 3 (web → clic en WhatsApp → reserva) es el caso intermedio: la
sesión original en la landing SIGUE contando como web (nunca tuvo
link_token), y el evento click_whatsapp que ya se registra ahí es
exactamente el "% que hizo click en WhatsApp" que se pedía — pero la
reserva final, si se completó charlando con el bot, se sigue contando
también en la pestaña WhatsApp por teléfono: hoy no existe ningún dato que
pruebe con certeza que esa conversación específica es la misma persona
que la sesión web (WhatsApp no deja pasar ningún identificador a través
del link wa.me). Decisión explícita del dueño: dejarlo así por ahora en
vez de adivinar con una aproximación poco confiable.
"""
from datetime import date, timedelta
from typing import Optional
from sqlalchemy import create_engine, text
from app.core.config import settings

# Umbral de duración (segundos) para considerar una sesión "útil" — ver
# nota arriba.
_USEFUL_SESSION_SECONDS = 5

# Buckets del histograma de distribución de duración — mismos cortes que el
# artefacto que se le mostró al dueño antes de fijar el umbral de 5s.
_DURATION_BUCKETS = [
    (0, 0, "0s"),
    (0, 1, "<1s"),
    (1, 3, "1-3s"),
    (3, 10, "3-10s"),
    (10, 30, "10-30s"),
    (30, 60, "30-60s"),
    (60, 180, "1-3min"),
    (180, 600, "3-10min"),
    (600, 1800, "10-30min"),
    (1800, None, "30min+"),
]


def _source_engine():
    """Mismo patrón que sync_hotboat.py — conecta a la base de HotBoat
    (booking_visitor_events, all_appointments viven ahí, no en esta app)."""
    url = settings.HOTBOAT_DATABASE_URL or settings.DATABASE_URL
    return create_engine(url)


def get_web_traffic_daily(desde: date, hasta: date) -> dict:
    engine = _source_engine()
    hasta_excl = hasta + timedelta(days=1)  # rango inclusivo del lado del cliente

    # Sesiones que llegaron por un link que mandó el bot de WhatsApp — se
    # excluyen de TODO lo de abajo para que "sesión web" no cuente dos
    # veces a la misma persona (una vez acá, otra en la pestaña WhatsApp
    # por teléfono). Ver nota de clasificación en el docstring del módulo.
    _EXCLUDE_WHATSAPP_SESSIONS = """
        AND session_id NOT IN (
            SELECT session_id FROM booking_visitor_events
            WHERE link_token IS NOT NULL
              AND recorded_at >= :desde AND recorded_at < :hasta_excl
        )
    """

    with engine.connect() as conn:
        # Sesiones totales + útiles por día. Un CTE agrupa cada sesión a su
        # primer día visto y su duración (último evento menos primero),
        # luego se cuenta por día — evita contar dos veces una sesión que
        # cruzó medianoche.
        sessions_rows = conn.execute(text(f"""
            WITH session_days AS (
                SELECT
                    session_id,
                    MIN(DATE(recorded_at AT TIME ZONE 'America/Santiago')) AS day,
                    EXTRACT(EPOCH FROM (MAX(recorded_at) - MIN(recorded_at))) > :useful_seconds AS interacted
                FROM booking_visitor_events
                WHERE recorded_at >= :desde AND recorded_at < :hasta_excl
                {_EXCLUDE_WHATSAPP_SESSIONS}
                GROUP BY session_id
            )
            SELECT day, COUNT(*) AS total, COUNT(*) FILTER (WHERE interacted) AS useful
            FROM session_days
            GROUP BY day ORDER BY day
        """), {"useful_seconds": _USEFUL_SESSION_SECONDS, "desde": desde, "hasta_excl": hasta_excl}).fetchall()

        # Eventos puntuales por día (cada uno cuenta sesiones DISTINTAS con
        # ese evento ese día, no el total de disparos — dos clicks en el
        # mismo botón en la misma sesión cuentan una vez).
        event_rows = conn.execute(text(f"""
            SELECT
                DATE(recorded_at AT TIME ZONE 'America/Santiago') AS day,
                event_type,
                COUNT(DISTINCT session_id) AS n
            FROM booking_visitor_events
            WHERE recorded_at >= :desde AND recorded_at < :hasta_excl
              AND event_type IN ('click_whatsapp', 'click_reservar', 'view_precio', 'view_prices', 'date_selected', 'booking_completed')
              {_EXCLUDE_WHATSAPP_SESSIONS}
            GROUP BY day, event_type
        """), {"desde": desde, "hasta_excl": hasta_excl}).fetchall()

        # "Vio precio y se fue" — sesiones con view_precio/view_prices que
        # NUNCA llegaron a date_selected en esa misma sesión.
        price_left_rows = conn.execute(text(f"""
            WITH price_sessions AS (
                SELECT
                    session_id,
                    MIN(DATE(recorded_at AT TIME ZONE 'America/Santiago')) AS day,
                    BOOL_OR(event_type = 'date_selected') AS advanced
                FROM booking_visitor_events
                WHERE recorded_at >= :desde AND recorded_at < :hasta_excl
                  {_EXCLUDE_WHATSAPP_SESSIONS}
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

        # Pagos confirmados — pagos (registro real de transferencia/efectivo/
        # MercadoPago que el operador carga a mano) es la fuente real, NO
        # payment_status: ese solo se llena en el flujo automático de
        # Transbank y queda NULL en el 95% de las reservas confirmadas, la
        # mayoría de las cuales sí se pagaron, solo que a mano por WhatsApp
        # (transferencia + captura de pantalla). Corregido 2026-07-26:
        # 113 reservas tienen pagos real vs. solo 23 con payment_status
        # aprobado/completado — este cambio quintuplica el conteo real de
        # "pagó" (y por lo tanto la tasa de conversión, que antes se veía
        # muy por debajo de la real).
        paid_rows = conn.execute(text("""
            SELECT DATE(COALESCE(updated_at, created_at) AT TIME ZONE 'America/Santiago') AS day, COUNT(*) AS n
            FROM all_appointments
            WHERE (
                (pagos IS NOT NULL AND jsonb_array_length(pagos) > 0)
                OR payment_status IN ('approved', 'completed')
            )
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
    booking_completed_events = sum(r["booking_completed_events"] for r in daily)
    paid = sum(r["paid"] for r in daily)
    popup_fills = sum(r["popup_fills"] for r in daily)

    # Todas las tasas de esta sección (pop-up, WhatsApp, sistema de reservas)
    # se calculan sobre sesiones ÚTILES, no totales — a pedido del dueño:
    # tiene más sentido preguntar "de la gente que realmente estuvo en el
    # sitio, cuántos hicieron X" que diluir todo contra el total de
    # sesiones, la mayoría de las cuales son rebotes de <5s que nunca
    # tuvieron oportunidad real de hacer nada.
    base = useful_sessions or 1
    return {
        "total_sessions": total_sessions,
        "useful_sessions": useful_sessions,
        "bounce_rate": round((1 - useful_sessions / total_sessions) * 100, 1) if total_sessions else 0.0,
        "popup_fills": popup_fills,
        "popup_fill_rate": round(popup_fills / base * 100, 2) if useful_sessions else 0.0,
        "whatsapp_clicks": whatsapp_clicks,
        "whatsapp_click_rate": round(whatsapp_clicks / base * 100, 2) if useful_sessions else 0.0,
        "went_to_booking": went_to_booking,
        "went_to_booking_rate": round(went_to_booking / base * 100, 2) if useful_sessions else 0.0,
        "viewed_price": viewed_price,
        "viewed_price_rate": round(viewed_price / base * 100, 2) if useful_sessions else 0.0,
        "viewed_price_left": viewed_price_left,
        "found_expensive_rate": round(viewed_price_left / viewed_price * 100, 1) if viewed_price else 0.0,
        "selected_date": selected_date,
        "selected_date_rate": round(selected_date / base * 100, 2) if useful_sessions else 0.0,
        "booking_completed_events": booking_completed_events,
        "reserved_rate": round(booking_completed_events / base * 100, 2) if useful_sessions else 0.0,
        "paid": paid,
        "conversion_rate": round(paid / base * 100, 2) if useful_sessions else 0.0,
    }


def get_session_duration_histogram(desde: date, hasta: date) -> dict:
    """Distribución de duración de sesión (mismos buckets que el artefacto
    mostrado al dueño antes de fijar el umbral de 5s en _USEFUL_SESSION_SECONDS
    arriba) — no varía por día/semana/mes, es una foto del rango completo."""
    engine = _source_engine()
    hasta_excl = hasta + timedelta(days=1)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                EXTRACT(EPOCH FROM (MAX(recorded_at) - MIN(recorded_at))) AS seconds
            FROM booking_visitor_events
            WHERE recorded_at >= :desde AND recorded_at < :hasta_excl
              AND session_id NOT IN (
                  SELECT session_id FROM booking_visitor_events
                  WHERE link_token IS NOT NULL
                    AND recorded_at >= :desde AND recorded_at < :hasta_excl
              )
            GROUP BY session_id
        """), {"desde": desde, "hasta_excl": hasta_excl}).fetchall()

    def _bucket_for(seconds: float) -> str:
        if seconds == 0: return "0s"
        if seconds < 1: return "<1s"
        if seconds < 3: return "1-3s"
        if seconds < 10: return "3-10s"
        if seconds < 30: return "10-30s"
        if seconds < 60: return "30-60s"
        if seconds < 180: return "1-3min"
        if seconds < 600: return "3-10min"
        if seconds < 1800: return "10-30min"
        return "30min+"

    counts = {label: 0 for (_, _, label) in _DURATION_BUCKETS}
    useful_counts = {label: 0 for (_, _, label) in _DURATION_BUCKETS}
    for (seconds,) in rows:
        label = _bucket_for(seconds)
        counts[label] += 1
        if seconds > _USEFUL_SESSION_SECONDS:
            useful_counts[label] += 1

    total = sum(counts.values())
    buckets = [
        {
            "label": label,
            "n": counts[label],
            "n_useful": useful_counts[label],
            "pct": round(counts[label] / total * 100, 1) if total else 0.0,
        }
        for (_, _, label) in _DURATION_BUCKETS
    ]

    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "total_sessions": total, "buckets": buckets}
