"""
Reduce todas las señales de origen de tráfico (utm_source/medium, referrer,
fbclid, contacts_crm.platform) a 3 buckets fijos: "meta" / "google" / "otro"
— el nivel de detalle pedido para la pestaña "Fuentes" (comparar dónde
invertir, no desglosar por anuncio individual — eso ya lo hace la pestaña
Anuncios, y solo es confiable para leads que pasaron por WhatsApp).

Dos contextos distintos alimentan el mismo reductor, porque parten de
señales distintas (inevitable, es el mismo patrón que ya existe entre
"flujo" y "canal" siendo dos lentes distintas sobre la misma reserva):

- Sesiones web anónimas (antes de tener teléfono): no hay fila en
  contacts_crm todavía, así que se bucketea directo desde
  booking_visitor_events.referrer/utm_source/utm_medium — misma lógica
  de palabras clave que ya usan _referrer_label()/_platform_label() en
  hotboat-whatsapp/app/booking/router.py (~línea 2615-2696), PORTADA acá
  (no importada — son despliegues/repos distintos). Si se cambian esas
  palabras clave allá, replicar el cambio acá.
- Teléfonos ya identificados (reservas, conversaciones de WhatsApp): usa
  contacts_crm.platform, que crm_sync.py ya calcula y persiste con
  _derive_platform() (facebook/instagram/google/tiktok/whatsapp/None) —
  no hace falta releer utm/referrer, ya está resuelto ahí.
"""

# Reductor único — el único lugar que decide qué colapsa a qué bucket, para
# que las dos consultas de abajo (sesión vs. teléfono) nunca puedan divergir
# en el CRITERIO de reducción, solo en la señal de entrada.
def bucket_3(platform5: str | None) -> str:
    p = (platform5 or "").strip().lower()
    if p in ("facebook", "instagram"):
        return "meta"
    if p == "google":
        return "google"
    return "otro"


# CASE SQL sobre columnas de booking_visitor_events (referrer, utm_source,
# utm_medium) — mismo orden de prioridad que _referrer_label()/
# _platform_label(): referrer primero (los navegadores in-app de TikTok/
# Instagram suelen borrar el referrer, pero cuando está presente es la señal
# más confiable), utm_source+utm_medium como respaldo. Ya reducido a los 3
# buckets finales, no a las 5 categorías intermedias.
#
# \yig\y (word boundary, no substring) — los propios links de campaña de
# HotBoat usan "ig" como utm_source corto para Instagram (ej.
# utm_source=ig&utm_medium=social&utm_content=link_in_bio). Sin este check
# esas sesiones caían en "otro" cuando el referrer venía vacío (navegador
# in-app de Instagram) — verificado 2026-08-06 comparando el CASE viejo vs
# nuevo sobre el mismo rango de 60 días: 29 de 5485 sesiones "otro" pasan a
# "meta" (small pero real; el resto de "otro" no tiene ninguna señal en
# absoluto — referrer y utm ambos vacíos — no es recuperable con reglas).
SESSION_PLATFORM_BUCKET_SQL = r"""
    CASE
        WHEN referrer ~* 'instagram' THEN 'meta'
        WHEN referrer ~* '(facebook|fb\.com)' THEN 'meta'
        WHEN referrer ~* 'google' THEN 'google'
        WHEN (COALESCE(utm_source,'') || ' ' || COALESCE(utm_medium,'')) ~* '(google|adwords|gclid)' THEN 'google'
        WHEN (COALESCE(utm_source,'') || ' ' || COALESCE(utm_medium,'')) ~* '(instagram|\yig\y)' THEN 'meta'
        WHEN (COALESCE(utm_source,'') || ' ' || COALESCE(utm_medium,'')) ~* '(facebook|\yfb\y|\ymeta\y)' THEN 'meta'
        ELSE 'otro'
    END
"""

# Variante agregada de SESSION_PLATFORM_BUCKET_SQL, para usar en un HAVING
# después de agrupar por session_id (referrer/utm_source/utm_medium no
# cambian dentro de una sesión, pero solo suelen venir en la primera fila —
# MAX() se queda con el único valor no-nulo presente en cualquier fila de esa
# sesión). Filtrar fila por fila con la versión no agregada sesgaría el
# MIN/MAX(recorded_at) de duración de sesión al descartar filas sin utm/
# referrer propio (ej. un click posterior dentro de la misma sesión).
SESSION_PLATFORM_BUCKET_SQL_AGG = SESSION_PLATFORM_BUCKET_SQL.replace(
    "referrer", "MAX(referrer)"
).replace("utm_source", "MAX(utm_source)").replace("utm_medium", "MAX(utm_medium)")


# CASE SQL sobre contacts_crm.platform, ya calculado por crm_sync.py — la
# query que use esto debe tener `contacts_crm cc` joineado por teléfono
# normalizado (regexp_replace(telefono,'[^0-9]','','g'), mismo patrón que
# PHONE_FLUJO_LATERAL / whatsapp_traffic_analytics.py — NO el join sin
# normalizar que usa ads.py, más frágil). Sin respaldo de sesión web — ver
# cc_platform_bucket_sql() más abajo para la versión CON ese respaldo.
CC_PLATFORM_BUCKET_SQL = """
    CASE
        WHEN cc.platform IN ('facebook', 'instagram') THEN 'meta'
        WHEN cc.platform = 'google' THEN 'google'
        ELSE 'otro'
    END
"""


# Respaldo cuando contacts_crm.platform no tiene nada (el caso más común:
# WhatsApp orgánico, nadie pagó un anuncio ni hubo checkout web con UTM) —
# busca si ese teléfono tuvo una sesión web orgánica ANTES (mismo criterio de
# vínculo que PHONE_FLUJO_LATERAL: booking_visitor_identity por teléfono o
# visitor_id, excluyendo sesiones que llegaron por link del bot) y usa el
# bucket de la señal más antigua (referrer/utm suele venir solo en el primer
# evento registrado). Agregado 2026-08-06 a pedido del dueño: "en WhatsApp
# podría saber cuándo la gente viene desde mi página web" — sí, exactamente
# el mismo vínculo que ya usa Flujo 3, solo que antes no se usaba también
# para clasificar plataforma. Medido antes de implementar: recupera ~2% del
# bucket "otro" de WhatsApp en una ventana de 60 días — real pero chico hoy,
# la mayoría de "otro" nunca tuvo ninguna sesión web vinculada.
def web_session_platform_lateral(phone_expr: str, alias: str = "lws") -> str:
    # UNION ALL de dos joins simples (session_id / visitor_id por separado),
    # NO "ON bve.session_id = bvi.session_id OR bve.visitor_id = bvi.visitor_id"
    # — ese OR le impedía al planner usar idx_bve_sid/idx_bve_vid y lo hacía
    # manejar el nested loop desde booking_visitor_events (~160k filas) en vez
    # de desde booking_visitor_identity (51 filas), una vez POR CADA teléfono
    # de la consulta externa: get_platform_comparison tardaba 2+ minutos.
    # Cada rama del UNION ALL es un join de 2 columnas indexadas sin OR, así
    # que el planner arranca por bvi (filtrado por teléfono, casi siempre 0
    # filas) y usa el índice para ir a bve solo cuando corresponde — medido
    # después del fix: <1s. Ver idx_bvi_phone_norm en hotboat-whatsapp/
    # app/booking/db.py (índice de expresión nuevo, aunque con solo 51 filas
    # en booking_visitor_identity el índice en sí no era el problema).
    return f"""
        LEFT JOIN LATERAL (
            SELECT bucket FROM (
                SELECT {SESSION_PLATFORM_BUCKET_SQL} AS bucket, bve.recorded_at
                FROM booking_visitor_identity bvi
                JOIN booking_visitor_events bve ON bve.session_id = bvi.session_id
                WHERE regexp_replace(bvi.phone, '[^0-9]', '', 'g') = {phone_expr}
                  AND bve.link_token IS NULL
                UNION ALL
                SELECT {SESSION_PLATFORM_BUCKET_SQL} AS bucket, bve.recorded_at
                FROM booking_visitor_identity bvi
                JOIN booking_visitor_events bve ON bve.visitor_id = bvi.visitor_id
                WHERE bvi.visitor_id IS NOT NULL
                  AND regexp_replace(bvi.phone, '[^0-9]', '', 'g') = {phone_expr}
                  AND bve.link_token IS NULL
            ) combined
            ORDER BY recorded_at ASC
            LIMIT 1
        ) {alias} ON true
    """


# Versión de CC_PLATFORM_BUCKET_SQL CON el respaldo de sesión web — requiere
# que la query también tenga web_session_platform_lateral(...) joineado con
# el mismo `alias`. Nunca puede dar un resultado PEOR que CC_PLATFORM_BUCKET_SQL
# solo (si no hay sesión vinculada, cae exactamente al mismo 'otro' de antes).
def cc_platform_bucket_sql(alias: str = "lws") -> str:
    return f"""
        CASE
            WHEN cc.platform IN ('facebook', 'instagram') THEN 'meta'
            WHEN cc.platform = 'google' THEN 'google'
            WHEN {alias}.bucket IN ('meta', 'google') THEN {alias}.bucket
            ELSE 'otro'
        END
    """
