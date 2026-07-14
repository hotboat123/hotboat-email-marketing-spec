"""
Analíticas de anuncios de Meta (gasto, CPC, costo por conversación) leídas
directo de meta_ads_insights/meta_ads/meta_adsets/meta_campaigns en la
Postgres compartida (mismo ETL de Meta Ads que ya alimenta esas tablas,
ver hotboat-whatsapp). Solo lectura — no se escribe nada de vuelta.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlmodel import Session

from app.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.services.sync_hotboat import _source_engine

router = APIRouter()

Level = Literal["ad", "adset", "campaign"]

# "Conversación" = mensaje de WhatsApp iniciado desde el anuncio (lo que Meta
# llama messaging_conversation_started) — el mismo criterio que usa Meta Ads
# Manager para "costo por conversación".
_CONVERSATION_ACTIONS = [
    "onsite_conversion.messaging_conversation_started_7d",
    "onsite_conversion.messaging_conversation_started",
    "messaging_conversation_started",
]

# JOINs y columna id/name/status por nivel — claves fijas (whitelist), nunca
# vienen de input del usuario directo, así que interpolarlas en el SQL es seguro.
_LEVEL_JOINS = {
    "ad": """
        FROM meta_ads_insights i
        JOIN meta_ads a ON a.id = i.ad_id
        LEFT JOIN meta_adsets s ON s.id = a.adset_id
        LEFT JOIN meta_campaigns c ON c.id = a.campaign_id
    """,
    "adset": """
        FROM meta_ads_insights i
        JOIN meta_ads a ON a.id = i.ad_id
        JOIN meta_adsets s ON s.id = a.adset_id
        LEFT JOIN meta_campaigns c ON c.id = s.campaign_id
    """,
    "campaign": """
        FROM meta_ads_insights i
        JOIN meta_ads a ON a.id = i.ad_id
        JOIN meta_campaigns c ON c.id = a.campaign_id
    """,
}

_LEVEL_COLS = {
    "ad": ("a.id", "a.name", "a.status"),
    "adset": ("s.id", "s.name", "s.status"),
    "campaign": ("c.id", "c.name", "c.status"),
}


def _conversations_sql() -> str:
    actions_list = ",".join(f"'{a}'" for a in _CONVERSATION_ACTIONS)
    return f"meta_fn_action_types_sum(i.actions, ARRAY[{actions_list}])"


def _require_level(level: str) -> None:
    if level not in _LEVEL_JOINS:
        raise HTTPException(status_code=400, detail="level debe ser ad, adset o campaign")


@router.get("/summary")
def ads_summary(
    level: Level = Query("ad"),
    _: User = Depends(get_current_user),
):
    """Gasto/CPC/costo por conversación acumulado por anuncio, conjunto de
    anuncios o campaña — según `level`. Sin rango de fechas: es todo el
    historial importado (ver first_date/last_date por fila)."""
    _require_level(level)
    id_col, name_col, status_col = _LEVEL_COLS[level]
    adset_name_sel = "s.name" if level == "ad" else "NULL"
    adset_group = ", s.name" if level == "ad" else ""

    sql = f"""
        SELECT {id_col} AS id, {name_col} AS name, {status_col} AS status,
               c.name AS campaign_name,
               {adset_name_sel} AS adset_name,
               SUM(i.spend) AS spend,
               SUM(i.clicks) AS clicks,
               SUM({_conversations_sql()}) AS conversations_started,
               MIN(i.date_start) AS first_date,
               MAX(i.date_start) AS last_date
        {_LEVEL_JOINS[level]}
        WHERE {id_col} IS NOT NULL
        GROUP BY {id_col}, {name_col}, {status_col}, c.name{adset_group}
        ORDER BY spend DESC
    """
    try:
        engine = _source_engine()
        with engine.connect() as conn:
            rows = conn.execute(text(sql)).all()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo leer meta_ads_insights: {exc}")

    return [_summary_row(r) for r in rows]


def _summary_row(r) -> dict:
    spend = float(r.spend or 0)
    clicks = float(r.clicks or 0)
    conversations = float(r.conversations_started or 0)
    return {
        "id": r.id,
        "name": r.name,
        "status": r.status,
        "campaign_name": r.campaign_name,
        "adset_name": r.adset_name,
        "spend": round(spend),
        "clicks": int(clicks),
        "cpc": round(spend / clicks, 1) if clicks else None,
        "conversations_started": int(conversations),
        "cost_per_conversation": round(spend / conversations, 1) if conversations else None,
        "first_date": r.first_date.isoformat() if r.first_date else None,
        "last_date": r.last_date.isoformat() if r.last_date else None,
    }


@router.get("/timeseries")
def ads_timeseries(
    level: Level = Query("ad"),
    id: str = Query(...),
    _: User = Depends(get_current_user),
):
    """Serie diaria (gasto, clicks, CPC, conversaciones, costo/conversación)
    para un anuncio/conjunto/campaña puntual — para graficar su evolución."""
    _require_level(level)
    id_col, name_col, status_col = _LEVEL_COLS[level]

    sql = f"""
        SELECT i.date_start AS date,
               SUM(i.spend) AS spend,
               SUM(i.clicks) AS clicks,
               SUM({_conversations_sql()}) AS conversations_started
        {_LEVEL_JOINS[level]}
        WHERE {id_col} = :id
        GROUP BY i.date_start
        ORDER BY i.date_start
    """
    name_sql = f"SELECT DISTINCT {name_col} AS name {_LEVEL_JOINS[level]} WHERE {id_col} = :id LIMIT 1"

    # Nombres de anuncio bajo este nivel (para nivel "ad" es solo el propio; para
    # adset/campaign, todos los anuncios que caen adentro) — se usan para buscar
    # reservas confirmadas cuyo ad_source matchea exactamente alguno de estos.
    if level == "ad":
        ad_names_sql = "SELECT name FROM meta_ads WHERE id = :id AND name IS NOT NULL"
    elif level == "adset":
        ad_names_sql = "SELECT DISTINCT name FROM meta_ads WHERE adset_id = :id AND name IS NOT NULL"
    else:
        ad_names_sql = "SELECT DISTINCT name FROM meta_ads WHERE campaign_id = :id AND name IS NOT NULL"

    try:
        engine = _source_engine()
        with engine.connect() as conn:
            rows = conn.execute(text(sql), {"id": id}).all()
            name_row = conn.execute(text(name_sql), {"id": id}).first()
            ad_names = [r[0] for r in conn.execute(text(ad_names_sql), {"id": id}).all()]
            bookings = _booking_days_for_names(conn, ad_names)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo leer meta_ads_insights: {exc}")

    if not rows:
        raise HTTPException(status_code=404, detail="Sin datos para ese id")

    return {
        "id": id,
        "name": name_row.name if name_row else id,
        "points": [
            {
                "date": r.date.isoformat(),
                "spend": float(r.spend or 0),
                "clicks": int(r.clicks or 0),
                "cpc": round(float(r.spend or 0) / float(r.clicks), 1) if r.clicks else None,
                "conversations_started": int(r.conversations_started or 0),
                "cost_per_conversation": (
                    round(float(r.spend or 0) / float(r.conversations_started), 1)
                    if r.conversations_started else None
                ),
            }
            for r in rows
        ],
        # Reservas confirmadas reales cuyo ad_source matchea el/los nombre(s) de
        # este anuncio/conjunto/campaña, con fecha confiable (paid_at, o
        # created_at excluyendo 'sheets' — esa fuente importa en bloque con una
        # sola fecha ficticia compartida para cientos de filas, así que se
        # excluye para no fabricar un pico falso). Son pocas — se muestran como
        # marcas puntuales sobre los gráficos, no como una tasa diaria (con esta
        # densidad de datos, una tasa % por día sería casi siempre 0 o 100%).
        "bookings": bookings,
    }


def _booking_days_for_names(conn, ad_names: list[str]) -> list[dict]:
    if not ad_names:
        return []
    rows = conn.execute(
        text("""
            SELECT COALESCE(a.paid_at, a.created_at)::date AS day, COUNT(*) AS bookings
            FROM all_appointments a
            JOIN contacts_crm cc ON cc.phone = a.telefono
            WHERE a.status = 'confirmed'
              AND a.source <> 'sheets'
              AND lower(cc.ad_source) = ANY(:names)
            GROUP BY 1
            ORDER BY 1
        """),
        {"names": [n.lower() for n in ad_names]},
    ).all()
    return [{"date": r.day.isoformat(), "count": int(r.bookings)} for r in rows]
