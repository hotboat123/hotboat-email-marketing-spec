from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from app.core.deps import get_current_user
from app.models.user import User
from app.services.web_traffic_analytics import get_web_traffic_daily, get_session_duration_histogram

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
