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
SESSION_PLATFORM_BUCKET_SQL = r"""
    CASE
        WHEN referrer ~* 'instagram' THEN 'meta'
        WHEN referrer ~* '(facebook|fb\.com)' THEN 'meta'
        WHEN referrer ~* 'google' THEN 'google'
        WHEN (COALESCE(utm_source,'') || ' ' || COALESCE(utm_medium,'')) ~* '(google|adwords|gclid)' THEN 'google'
        WHEN (COALESCE(utm_source,'') || ' ' || COALESCE(utm_medium,'')) ~* 'instagram' THEN 'meta'
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
# normalizar que usa ads.py, más frágil).
CC_PLATFORM_BUCKET_SQL = """
    CASE
        WHEN cc.platform IN ('facebook', 'instagram') THEN 'meta'
        WHEN cc.platform = 'google' THEN 'google'
        ELSE 'otro'
    END
"""
