from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from app.core.deps import get_current_user
from app.models.user import User
from app.services.web_traffic_analytics import get_web_traffic_daily

router = APIRouter()


@router.get("/daily")
def web_traffic_daily(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Tráfico diario del sitio (landing hotboat.cl + booking-soft.html) —
    ver app/services/web_traffic_analytics.py para las definiciones exactas
    de cada métrica (sesión útil, "encontró caro", conversión, etc.)."""
    if hasta is None:
        hasta = date.today()
    if desde is None:
        desde = hasta - timedelta(days=61)  # ~2 meses por defecto
    return get_web_traffic_daily(desde, hasta)
