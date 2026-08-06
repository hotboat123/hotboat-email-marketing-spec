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
exactamente el "% que hizo click en WhatsApp" que se pedía.

Atribución del pago para Flujo 3 (agregado 2026-08-04, reemplaza la
decisión anterior de "hoy no existe dato para probarlo, dejarlo en
WhatsApp"): esa decisión era de cuando esto era una exclusión ciega por
teléfono (cualquier teléfono que alguna vez escribió por WhatsApp se
sacaba de Web entero). Después se construyó, para el drill-down de la
pestaña WhatsApp, una heurística real de orden cronológico
(booking_visitor_identity cruzado con booking_visitor_events): si esa
persona tiene una sesión web orgánica ANTES de su primer mensaje de
WhatsApp, es evidencia de que la web fue la entrada real. El dueño pidió
usar esa misma heurística para decidir DÓNDE se cuenta la venta, no solo
para mostrarla en el detalle — ver PHONE_FLUJO_LATERAL.

Corrección 2026-08-04 (mismo día): la primera versión de esa heurística
comparaba "¿ALGUNA VEZ tuvo sesión web antes de escribir por WhatsApp?"
sin mirar cuándo se hizo ESTA reserva puntual — así que alguien que
reservó por la web y recién DESPUÉS recibió un WhatsApp (ej. un mensaje
de seguimiento al día siguiente) quedaba mal clasificado como flujo_3,
cuando ese WhatsApp no tuvo ningún rol en la venta (caso real: Felipe
Ortega, reservó el 28/07, WhatsApp del 29/07). Ahora solo cuenta un
mensaje de WhatsApp si pasó ANTES de created_at de la reserva — por eso
es un LEFT JOIN LATERAL correlacionado a cada fila de all_appointments,
no una tabla precalculada por teléfono (el flujo de una reserva puede
depender de CUÁNDO se hizo, no es un hecho fijo de la persona).
"""
from datetime import date, timedelta
from typing import Optional
from sqlalchemy import create_engine, text
from app.core.config import settings

# Umbral de duración (segundos) para considerar una sesión "útil" — ver
# nota arriba.
_USEFUL_SESSION_SECONDS = 5

# Clasificación de flujo POR RESERVA — ver nota "Atribución del pago para
# Flujo 3" / "Corrección 2026-08-04" arriba. Requiere que la consulta que
# use esto tenga all_appointments aliased como "a" (usa a.telefono y
# a.created_at) — el JOIN LATERAL en sí agrega la columna pf.flujo, que
# nunca es NULL (el CASE siempre resuelve a uno de los 3 valores).
# Reutilizada tal cual por whatsapp_traffic_analytics.py — no duplicar
# esta lógica ahí, importarla de acá, para que ambas pestañas siempre
# clasifiquen a la misma reserva de la misma forma.
PHONE_FLUJO_LATERAL = """
    LEFT JOIN LATERAL (
        SELECT
            CASE
                WHEN fm.first_msg_before IS NULL THEN 'flujo_2'
                WHEN fo.first_organic_before IS NOT NULL THEN 'flujo_3'
                ELSE 'flujo_1'
            END AS flujo
        FROM (
            SELECT MIN(wc.created_at) AS first_msg_before
            FROM whatsapp_conversations wc
            WHERE wc.phone_number = regexp_replace(a.telefono, '[^0-9]', '', 'g')
              AND wc.created_at < a.created_at
        ) fm
        LEFT JOIN LATERAL (
            SELECT MIN(bve.recorded_at) AS first_organic_before
            FROM booking_visitor_identity bvi
            JOIN booking_visitor_events bve
              ON bve.session_id = bvi.session_id
                 OR (bvi.visitor_id IS NOT NULL AND bve.visitor_id = bvi.visitor_id)
            WHERE regexp_replace(bvi.phone, '[^0-9]', '', 'g') = regexp_replace(a.telefono, '[^0-9]', '', 'g')
              AND bve.link_token IS NULL
              AND bve.recorded_at < fm.first_msg_before
        ) fo ON fm.first_msg_before IS NOT NULL
    ) pf ON true
"""

# Excluye SOLO las reservas "flujo_1" (WhatsApp puro, sin evidencia de
# sesión web antes) de los conteos de pago de esta página — los "flujo_3"
# (web → WhatsApp) se quedan, ya que la sesión web fue la entrada real.
# Requiere PHONE_FLUJO_LATERAL en la misma consulta.
_EXCLUDE_FLUJO1_PHONES = "AND pf.flujo != 'flujo_1'"

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


def get_web_traffic_daily(desde: date, hasta: date, platform: str | None = None) -> dict:
    """platform (opcional): "meta"/"google"/"otro" — filtra sesiones por
    SESSION_PLATFORM_BUCKET_SQL y reservas por CC_PLATFORM_BUCKET_SQL (ver
    platform_attribution.py). Sin este parámetro, comportamiento 100%
    idéntico a antes — usado por la pestaña "Tráfico Web" existente."""
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

    from app.services.platform_attribution import SESSION_PLATFORM_BUCKET_SQL_AGG, CC_PLATFORM_BUCKET_SQL
    # session_id IN (...) con HAVING sobre la versión agregada (MAX) —
    # nunca un WHERE fila-por-fila: referrer/utm_source/utm_medium suelen
    # venir solo en la primera fila de la sesión, filtrar por fila antes de
    # agrupar sesgaría el MIN/MAX(recorded_at) de duración al descartar
    # filas sin utm/referrer propio (ej. un click posterior en la sesión).
    _SESSION_PLATFORM_FILTER = f"""
        AND session_id IN (
            SELECT session_id FROM booking_visitor_events
            WHERE recorded_at >= :desde AND recorded_at < :hasta_excl
            GROUP BY session_id
            HAVING {SESSION_PLATFORM_BUCKET_SQL_AGG} = :platform
        )
    """ if platform else ""
    _params_platform = {"platform": platform} if platform else {}

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
                {_SESSION_PLATFORM_FILTER}
                GROUP BY session_id
            )
            SELECT day, COUNT(*) AS total, COUNT(*) FILTER (WHERE interacted) AS useful
            FROM session_days
            GROUP BY day ORDER BY day
        """), {"useful_seconds": _USEFUL_SESSION_SECONDS, "desde": desde, "hasta_excl": hasta_excl, **_params_platform}).fetchall()

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
              {_SESSION_PLATFORM_FILTER}
            GROUP BY day, event_type
        """), {"desde": desde, "hasta_excl": hasta_excl, **_params_platform}).fetchall()

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
                  {_SESSION_PLATFORM_FILTER}
                  AND session_id IN (
                      SELECT session_id FROM booking_visitor_events
                      WHERE event_type IN ('view_precio', 'view_prices')
                        AND recorded_at >= :desde AND recorded_at < :hasta_excl
                  )
                GROUP BY session_id
            )
            SELECT day, COUNT(*) FILTER (WHERE NOT advanced) AS left_after_price, COUNT(*) AS saw_price
            FROM price_sessions GROUP BY day ORDER BY day
        """), {"desde": desde, "hasta_excl": hasta_excl, **_params_platform}).fetchall()

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
        #
        # Excluye reservas "flujo_1" (WhatsApp puro, sin evidencia de sesión
        # web antes de escribir) — ver PHONE_FLUJO_LATERAL y la nota
        # "Atribución del pago para Flujo 3" en el docstring del módulo. Las
        # "flujo_3" (web → WhatsApp) se quedan acá, no en la pestaña WhatsApp.
        #
        # Se cuenta por created_at (cuándo se creó la reserva), no por
        # updated_at/fecha de pago — a pedido del dueño 2026-08-04: lo que
        # importa para atribuir la conversión a un día es cuándo la persona
        # reservó, no cuándo se registró el pago (que puede llegar días
        # después, ej. transferencia manual).
        #
        # El filtro de rango compara por DATE(... AT TIME ZONE 'America/
        # Santiago'), igual que el GROUP BY — no created_at crudo contra
        # :desde/:hasta_excl (que Postgres interpreta en UTC). Si no, una
        # reserva creada tarde en la noche de Chile (ya "día siguiente" en
        # UTC) se le atribuía bien al día de Chile en el agregado pero
        # quedaba afuera del rango de un día puntual — el drill-down de un
        # solo día terminaba con menos filas que el número que el propio
        # gráfico mostraba para ese día.
        _PLATFORM_JOIN = """
            LEFT JOIN contacts_crm cc
              ON regexp_replace(cc.phone, '[^0-9]', '', 'g') = regexp_replace(a.telefono, '[^0-9]', '', 'g')
        """ if platform else ""
        _PLATFORM_FILTER_PAID = f"AND {CC_PLATFORM_BUCKET_SQL} = :platform" if platform else ""
        paid_rows = conn.execute(text(f"""
            SELECT DATE(a.created_at AT TIME ZONE 'America/Santiago') AS day, COUNT(*) AS n
            FROM all_appointments a
            {PHONE_FLUJO_LATERAL}
            {_PLATFORM_JOIN}
            WHERE (
                (a.pagos IS NOT NULL AND jsonb_array_length(a.pagos) > 0)
                OR a.payment_status IN ('approved', 'completed')
            )
              AND DATE(a.created_at AT TIME ZONE 'America/Santiago') >= :desde
              AND DATE(a.created_at AT TIME ZONE 'America/Santiago') <= :hasta
              {_EXCLUDE_FLUJO1_PHONES}
              {_PLATFORM_FILTER_PAID}
            GROUP BY day ORDER BY day
        """), {"desde": desde, "hasta": hasta, **_params_platform}).fetchall()

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

    # form_submissions no tiene session_id/teléfono para cruzar contra un
    # bucket de plataforma — con un filtro de plataforma activo se deja en
    # 0 (no atribuible) en vez de mostrar el total sin filtrar, que
    # confundiría al mezclar un número de "todas las fuentes" dentro de una
    # vista que dice estar filtrada a una sola.
    if not platform:
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


def get_web_conversions_detail(desde: date, hasta: date, platform: str | None = None) -> list[dict]:
    """Quiénes son los "paid" que cuenta get_web_traffic_daily — mismo
    criterio de pago, de fecha (created_at en hora de Chile, no cuándo se
    pagó ni la fecha cruda en UTC — ver los dos comentarios en
    get_web_traffic_daily) y de exclusión de reservas flujo_1 que la
    agregada, para que la lista siempre calce con el número de la
    tarjeta. Incluye "flujo" (flujo_2 = sin WhatsApp antes de esta
    reserva, flujo_3 = sí, pero después de una sesión web — ver
    PHONE_FLUJO_LATERAL) para poder mostrar el % que igual pasó por
    WhatsApp en el camino. platform (opcional): ver get_web_traffic_daily."""
    from app.services.platform_attribution import CC_PLATFORM_BUCKET_SQL
    engine = _source_engine()

    _platform_join = """
        LEFT JOIN contacts_crm cc
          ON regexp_replace(cc.phone, '[^0-9]', '', 'g') = regexp_replace(a.telefono, '[^0-9]', '', 'g')
    """ if platform else ""
    _platform_filter = f"AND {CC_PLATFORM_BUCKET_SQL} = :platform" if platform else ""
    _params_platform = {"platform": platform} if platform else {}

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT
                a.id, a.appointment_id, a.nombre_cliente, a.email, a.telefono,
                a.servicio, a.fecha, a.hora, a.ingreso_total,
                a.created_at,
                pf.flujo
            FROM all_appointments a
            {PHONE_FLUJO_LATERAL}
            {_platform_join}
            WHERE (
                (a.pagos IS NOT NULL AND jsonb_array_length(a.pagos) > 0)
                OR a.payment_status IN ('approved', 'completed')
            )
              AND DATE(a.created_at AT TIME ZONE 'America/Santiago') >= :desde
              AND DATE(a.created_at AT TIME ZONE 'America/Santiago') <= :hasta
              {_EXCLUDE_FLUJO1_PHONES}
              {_platform_filter}
            ORDER BY a.created_at DESC
        """), {"desde": desde, "hasta": hasta, **_params_platform}).fetchall()

    return [
        {
            "booking_ref": r.appointment_id or f"AA-{r.id}",
            "name": r.nombre_cliente,
            "email": r.email,
            "phone": r.telefono,
            "servicio": r.servicio,
            "fecha": r.fecha.isoformat() if r.fecha else None,
            "hora": str(r.hora)[:5] if r.hora else None,
            "monto": float(r.ingreso_total) if r.ingreso_total else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "flujo": r.flujo or "flujo_2",
        }
        for r in rows
    ]


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
