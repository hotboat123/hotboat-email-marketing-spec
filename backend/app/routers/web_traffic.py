from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from app.core.deps import get_current_user
from app.models.user import User
from app.services.web_traffic_analytics import (
    get_web_traffic_daily, get_session_duration_histogram, get_web_conversions_detail,
)
from app.services.whatsapp_traffic_analytics import get_whatsapp_traffic_daily, get_whatsapp_conversions_detail

router = APIRouter()


def _default_range(desde: date, hasta: date) -> tuple[date, date]:
    if hasta is None:
        hasta = date.today()
    if desde is None:
        desde = hasta - timedelta(days=61)  # ~2 meses por defecto
    return desde, hasta


@router.get("/daily")
def web_traffic_daily(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Tráfico diario del sitio (landing hotboat.cl + booking-soft.html) —
    ver app/services/web_traffic_analytics.py para las definiciones exactas
    de cada métrica (sesión útil, "encontró caro", conversión, etc.)."""
    desde, hasta = _default_range(desde, hasta)
    return get_web_traffic_daily(desde, hasta)


@router.get("/duration-histogram")
def web_traffic_duration_histogram(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Distribución de cuánto tiempo pasan las sesiones en el sitio, para el
    rango de fechas elegido — no varía por día/semana/mes."""
    desde, hasta = _default_range(desde, hasta)
    return get_session_duration_histogram(desde, hasta)


@router.get("/whatsapp-daily")
def whatsapp_traffic_daily(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Tráfico diario de WhatsApp — ver app/services/whatsapp_traffic_analytics.py
    para las definiciones exactas (conversación útil, "encontró caro", etc.)."""
    desde, hasta = _default_range(desde, hasta)
    return get_whatsapp_traffic_daily(desde, hasta)


@router.get("/conversions")
def web_conversions_detail(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Quiénes son los "paid" de la pestaña web — mismo criterio y mismo
    número que la tarjeta de conversión."""
    desde, hasta = _default_range(desde, hasta)
    return get_web_conversions_detail(desde, hasta)


@router.get("/whatsapp-conversions")
def whatsapp_conversions_detail(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Quiénes son los "paid" de la pestaña WhatsApp, con clasificación por
    orden cronológico (flujo 1 vs flujo 3) — ver
    get_whatsapp_conversions_detail() para el criterio exacto."""
    desde, hasta = _default_range(desde, hasta)
    return get_whatsapp_conversions_detail(desde, hasta)
