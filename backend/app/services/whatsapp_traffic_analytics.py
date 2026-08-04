"""
Tráfico de WhatsApp, día a día — mismo tratamiento que web_traffic_analytics.py
para el sitio, pero sobre whatsapp_conversations (una fila por mensaje
entrante, con la respuesta del bot en la misma fila — ver hotboat-whatsapp).

Definiciones acordadas con el dueño del negocio (2026-07-26):
- "Conversación" = toda la actividad de un phone_number dentro del rango de
  fechas elegido, agrupada al día de su primer mensaje en ese rango (mismo
  criterio "cohorte" que el embudo del sitio: se evalúa toda la conversación,
  pero se cuenta en el día en que empezó).
- "Conversación útil" (no descartada) = 2 o más mensajes ENTRANTES del
  cliente. Elegido tras revisar los datos reales: de las conversaciones de
  1 solo mensaje, más del 90% es literalmente el texto autogenerado que
  manda WhatsApp al hacer click en un anuncio de Meta ("¡Hola! Quiero más
  información.") — el cliente nunca escribió nada él mismo. Es el
  equivalente de WhatsApp a los beacons automáticos page_visit/exit del
  sitio web.
- "Preguntó por precio" / "preguntó por fecha" = coincidencia de palabras
  clave en algún mensaje entrante — mismo vocabulario que ya usa el propio
  bot para decidir cuándo adjuntar el link de reserva en la respuesta de IA
  (ver _AI_LINK_WORTHY_KEYWORDS en hotboat-whatsapp/app/bot/conversation.py),
  para mantener consistencia con lo que el bot mismo ya considera "pregunta
  de precio/reserva".
- "Encontró caro" = preguntó por precio y NADA MÁS después (no preguntó
  fecha, no hizo click en el link, no reservó) — mismo criterio que
  "vio precio y se fue" en el sitio web.
- "Hizo click en el link" = tracked_quote_links.first_clicked_at no nulo,
  para algún link creado a nombre de ese teléfono.
- "Reservó" / "pagó" = cruce contra all_appointments por teléfono
  (normalizado sin "+" — los tres orígenes de teléfono en esta base no usan
  el mismo formato).
"""
from datetime import date, timedelta
from sqlalchemy import create_engine, text
from app.core.config import settings

_USEFUL_MIN_INCOMING = 2

# Mismo vocabulario que ConversationManager._AI_LINK_WORTHY_KEYWORDS en
# hotboat-whatsapp/app/bot/conversation.py — deliberadamente amplio, un
# falso positivo solo agrega una etiqueta de más, un falso negativo esconde
# una pregunta real de precio/reserva.
_PRICE_KEYWORDS_RE = r"(precio|precios|cuanto|cu[aá]nto|vale|sale|cuesta|valor|valores|cotiz)"
_DATE_KEYWORDS_RE = r"(fecha|disponib|horario|cu[aá]ndo|agend|reservar|reserva)"


def _source_engine():
    url = settings.HOTBOAT_DATABASE_URL or settings.DATABASE_URL
    return create_engine(url)


def get_whatsapp_traffic_daily(desde: date, hasta: date) -> dict:
    engine = _source_engine()
    hasta_excl = hasta + timedelta(days=1)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            WITH conv AS (
                SELECT
                    phone_number,
                    MIN(DATE(created_at AT TIME ZONE 'America/Santiago')) AS day,
                    COUNT(*) FILTER (WHERE direction = 'incoming') AS n_incoming,
                    BOOL_OR(direction = 'incoming' AND message_text ~* :price_re) AS asked_price,
                    BOOL_OR(direction = 'incoming' AND message_text ~* :date_re) AS asked_date
                FROM whatsapp_conversations
                WHERE created_at >= :desde AND created_at < :hasta_excl
                GROUP BY phone_number
            ),
            -- Normaliza el teléfono UNA vez por lead, no una vez por
            -- conversación — regexp_replace() dentro de un EXISTS por fila
            -- no puede usar el índice de all_appointments.telefono y
            -- termina escaneando la tabla completa por cada conversación.
            appt_phones AS (
                SELECT DISTINCT regexp_replace(telefono, '[^0-9]', '', 'g') AS phone
                FROM all_appointments WHERE telefono IS NOT NULL
            ),
            -- "pagó" real viene de pagos (registro real de transferencia/
            -- efectivo/MercadoPago que carga el operador a mano), NO de
            -- payment_status — ese solo se llena en el flujo automático de
            -- Transbank y queda NULL en el 95% de las reservas confirmadas,
            -- la mayoría de las cuales sí se pagaron, solo que a mano por
            -- WhatsApp (transferencia + captura de pantalla). Verificado:
            -- 113 reservas tienen pagos real vs. solo 23 con payment_status
            -- aprobado/completado.
            paid_phones AS (
                SELECT DISTINCT regexp_replace(telefono, '[^0-9]', '', 'g') AS phone
                FROM all_appointments
                WHERE telefono IS NOT NULL
                  AND (
                      (pagos IS NOT NULL AND jsonb_array_length(pagos) > 0)
                      OR payment_status IN ('approved', 'completed')
                  )
            ),
            clicked_phones AS (
                SELECT DISTINCT phone FROM tracked_quote_links WHERE first_clicked_at IS NOT NULL
            )
            SELECT
                c.day,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE c.n_incoming >= :useful_min) AS useful,
                COUNT(*) FILTER (WHERE c.asked_price) AS asked_price_n,
                COUNT(*) FILTER (WHERE c.asked_price AND NOT c.asked_date AND cl.phone IS NULL AND ap.phone IS NULL) AS found_expensive_n,
                COUNT(*) FILTER (WHERE c.asked_date) AS asked_date_n,
                COUNT(*) FILTER (WHERE cl.phone IS NOT NULL) AS clicked_link_n,
                COUNT(*) FILTER (WHERE ap.phone IS NOT NULL) AS reserved_n,
                COUNT(*) FILTER (WHERE pp.phone IS NOT NULL) AS paid_n
            FROM conv c
            LEFT JOIN clicked_phones cl ON cl.phone = c.phone_number
            LEFT JOIN appt_phones ap ON ap.phone = c.phone_number
            LEFT JOIN paid_phones pp ON pp.phone = c.phone_number
            GROUP BY c.day ORDER BY c.day
        """), {
            "price_re": _PRICE_KEYWORDS_RE, "date_re": _DATE_KEYWORDS_RE,
            "useful_min": _USEFUL_MIN_INCOMING,
            "desde": desde, "hasta_excl": hasta_excl,
        }).fetchall()

    by_day: dict = {}
    d = desde
    while d <= hasta:
        by_day[d.isoformat()] = {
            "day": d.isoformat(), "total_conversations": 0, "useful_conversations": 0,
            "asked_price": 0, "found_expensive": 0, "asked_date": 0,
            "clicked_link": 0, "reserved": 0, "paid": 0,
        }
        d += timedelta(days=1)

    for (day, total, useful, asked_price_n, found_expensive_n, asked_date_n,
         clicked_link_n, reserved_n, paid_n) in rows:
        key = day.isoformat()
        if key in by_day:
            by_day[key].update({
                "total_conversations": total, "useful_conversations": useful,
                "asked_price": asked_price_n, "found_expensive": found_expensive_n,
                "asked_date": asked_date_n, "clicked_link": clicked_link_n,
                "reserved": reserved_n, "paid": paid_n,
            })

    daily = []
    for row in by_day.values():
        useful = row["useful_conversations"]
        row["conversion_rate"] = round(row["paid"] / useful * 100, 2) if useful else 0.0
        row["found_expensive_rate"] = round(row["found_expensive"] / row["asked_price"] * 100, 1) if row["asked_price"] else 0.0
        daily.append(row)

    totals = _sum_totals(daily)
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "daily": daily, "totals": totals}


def get_whatsapp_conversions_detail(
    desde: date, hasta: date, cohort_from: date | None = None, cohort_to: date | None = None
) -> list[dict]:
    """Quiénes son los "paid" que cuenta get_whatsapp_traffic_daily, más una
    clasificación por orden cronológico real (no solo "mismo dispositivo
    alguna vez"): para cada reserva, se busca si ese teléfono tiene una
    identidad web (booking_visitor_identity, enlazada al reservar) con
    ALGUNA sesión orgánica (sin link_token — es decir, nunca llegó por un
    link que mandó el bot) cuyo primer evento sea ANTERIOR al primer
    mensaje de WhatsApp de ese teléfono. Si existe: la persona ya andaba
    por la web antes de escribir — flujo 3. Si no: no hay evidencia de que
    haya pasado por la web antes — flujo 1 (a falta de mejor dato).

    desde/hasta deben ser el MISMO rango completo que se le pasó a
    get_whatsapp_traffic_daily (no el día puntual que se está mirando) —
    la agregada le atribuye cada teléfono al día de su PRIMER mensaje
    dentro de ese rango completo ("cohorte"), así que angostar desde/hasta
    a un solo día cambiaría de qué mensaje se calcula ese "primer mensaje"
    y dejaría de calzar con el número de esa métrica. Para acotar el
    drill-down a un día (o bucket de semana/mes) puntual del gráfico, se
    usa cohort_from/cohort_to en cambio — filtran por el día de cohorte ya
    calculado sobre el rango completo, sin tocar ese cálculo."""
    engine = _source_engine()
    hasta_excl = hasta + timedelta(days=1)

    with engine.connect() as conn:
        rows = conn.execute(text("""
            WITH conv_first AS (
                -- Sin filtro de "conversación útil" (>=2 entrantes) a
                -- propósito: get_whatsapp_traffic_daily tampoco lo aplica a
                -- paid_n, solo a la métrica "useful" por separado — un
                -- "pagó" real no debería desaparecer de esta lista solo
                -- porque escribió un único mensaje.
                SELECT
                    phone_number,
                    MIN(created_at) AS first_msg_at,
                    MIN(DATE(created_at AT TIME ZONE 'America/Santiago')) AS day
                FROM whatsapp_conversations
                WHERE created_at >= :desde AND created_at < :hasta_excl
                GROUP BY phone_number
            ),
            paid_appts AS (
                SELECT
                    id, appointment_id, nombre_cliente, email, telefono,
                    servicio, fecha, hora, ingreso_total,
                    regexp_replace(telefono, '[^0-9]', '', 'g') AS phone_norm,
                    created_at
                FROM all_appointments
                WHERE telefono IS NOT NULL
                  AND (
                      (pagos IS NOT NULL AND jsonb_array_length(pagos) > 0)
                      OR payment_status IN ('approved', 'completed')
                  )
            ),
            matched AS (
                SELECT pa.*, cf.first_msg_at
                FROM paid_appts pa
                JOIN conv_first cf ON cf.phone_number = pa.phone_norm
                WHERE ((:cohort_from)::date IS NULL OR cf.day >= (:cohort_from)::date)
                  AND ((:cohort_to)::date IS NULL OR cf.day <= (:cohort_to)::date)
            ),
            identity AS (
                SELECT DISTINCT
                    regexp_replace(phone, '[^0-9]', '', 'g') AS phone_norm,
                    visitor_id, session_id
                FROM booking_visitor_identity
                WHERE phone IS NOT NULL
            ),
            organic_first AS (
                SELECT idn.phone_norm, MIN(bve.recorded_at) AS first_organic_at
                FROM identity idn
                JOIN booking_visitor_events bve
                  ON bve.session_id = idn.session_id
                     OR (idn.visitor_id IS NOT NULL AND bve.visitor_id = idn.visitor_id)
                WHERE bve.link_token IS NULL
                GROUP BY idn.phone_norm
            )
            SELECT m.*, o.first_organic_at
            FROM matched m
            LEFT JOIN organic_first o ON o.phone_norm = m.phone_norm
            ORDER BY m.created_at DESC
        """), {
            "desde": desde, "hasta_excl": hasta_excl,
            "cohort_from": cohort_from, "cohort_to": cohort_to,
        }).fetchall()

    def _naive(dt):
        return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt

    result = []
    for r in rows:
        organic_at, msg_at = _naive(r.first_organic_at), _naive(r.first_msg_at)
        if organic_at and msg_at and organic_at < msg_at:
            flujo = "flujo_3"
        else:
            flujo = "flujo_1"
        result.append({
            "booking_ref": r.appointment_id or f"AA-{r.id}",
            "name": r.nombre_cliente,
            "email": r.email,
            "phone": r.telefono,
            "servicio": r.servicio,
            "fecha": r.fecha.isoformat() if r.fecha else None,
            "hora": str(r.hora)[:5] if r.hora else None,
            "monto": float(r.ingreso_total) if r.ingreso_total else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "flujo": flujo,
            "first_whatsapp_msg_at": r.first_msg_at.isoformat() if r.first_msg_at else None,
            "first_web_organic_at": r.first_organic_at.isoformat() if r.first_organic_at else None,
        })
    return result


def _sum_totals(daily: list[dict]) -> dict:
    total_conversations = sum(r["total_conversations"] for r in daily)
    useful_conversations = sum(r["useful_conversations"] for r in daily)
    asked_price = sum(r["asked_price"] for r in daily)
    found_expensive = sum(r["found_expensive"] for r in daily)
    asked_date = sum(r["asked_date"] for r in daily)
    clicked_link = sum(r["clicked_link"] for r in daily)
    reserved = sum(r["reserved"] for r in daily)
    paid = sum(r["paid"] for r in daily)

    base = useful_conversations or 1
    return {
        "total_conversations": total_conversations,
        "useful_conversations": useful_conversations,
        "discard_rate": round((1 - useful_conversations / total_conversations) * 100, 1) if total_conversations else 0.0,
        "asked_price": asked_price,
        "asked_price_rate": round(asked_price / base * 100, 2) if useful_conversations else 0.0,
        "found_expensive": found_expensive,
        "found_expensive_rate": round(found_expensive / asked_price * 100, 2) if asked_price else 0.0,
        "asked_date": asked_date,
        "asked_date_rate": round(asked_date / base * 100, 2) if useful_conversations else 0.0,
        "clicked_link": clicked_link,
        "clicked_link_rate": round(clicked_link / base * 100, 2) if useful_conversations else 0.0,
        "reserved": reserved,
        "reserved_rate": round(reserved / base * 100, 2) if useful_conversations else 0.0,
        "paid": paid,
        "conversion_rate": round(paid / base * 100, 2) if useful_conversations else 0.0,
    }
