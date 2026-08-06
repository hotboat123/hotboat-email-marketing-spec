from datetime import date, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.deps import get_current_user
from app.models.user import User
from app.services.source_analytics import get_platform_comparison, get_flujo_platform_crosstab
from app.services.web_traffic_analytics import get_web_traffic_daily, get_web_conversions_detail
from app.services.whatsapp_traffic_analytics import get_whatsapp_traffic_daily, get_whatsapp_conversions_detail

router = APIRouter()

Platform = Literal["meta", "google", "otro"]
Channel = Literal["web", "whatsapp"]
_VALID_PLATFORMS = {"meta", "google", "otro"}


def _default_range(desde: date, hasta: date) -> tuple[date, date]:
    if hasta is None:
        hasta = date.today()
    if desde is None:
        desde = hasta - timedelta(days=61)
    return desde, hasta


def _parse_platforms(platform: Optional[str]) -> Optional[list[str]]:
    """`platform` acepta un solo bucket o varios separados por coma (ej.
    "meta,google" = Meta O Google, sin Otro — filtro multi-select de la
    pestaña Fuentes). None, vacío, o los 3 buckets = sin filtro (idéntico a
    la pestaña sin filtrar)."""
    if not platform:
        return None
    values = [p.strip() for p in platform.split(",") if p.strip()]
    invalid = [p for p in values if p not in _VALID_PLATFORMS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Plataforma inválida: {invalid}")
    if not values or set(values) >= _VALID_PLATFORMS:
        return None
    return values


@router.get("/comparison")
def comparison(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Tabla comparativa Google/Meta/Otro — sesiones/conversaciones,
    reservas pagadas, tasa de conversión, y (solo Meta) gasto real +
    costo por reserva. Ver app/services/source_analytics.py."""
    desde, hasta = _default_range(desde, hasta)
    return get_platform_comparison(desde, hasta)


@router.get("/crosstab")
def crosstab(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Tabla cruzada flujo (1/2/3) x plataforma (meta/google/otro)."""
    desde, hasta = _default_range(desde, hasta)
    return get_flujo_platform_crosstab(desde, hasta)


@router.get("/daily")
def daily(
    channel: Channel = Query("web"),
    platform: Optional[str] = Query(default=None, description="meta,google,otro (uno o varios separados por coma)"),
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Mismo shape que /api/web-traffic/daily y /whatsapp-daily, pero con un
    filtro de plataforma opcional (uno o varios buckets a la vez) — reusa
    las mismas funciones (sin `platform`, resultado idéntico a esas
    pestañas)."""
    desde, hasta = _default_range(desde, hasta)
    platforms = _parse_platforms(platform)
    if channel == "web":
        return get_web_traffic_daily(desde, hasta, platforms=platforms)
    return get_whatsapp_traffic_daily(desde, hasta, platforms=platforms)


@router.get("/conversions")
def conversions(
    channel: Channel = Query("web"),
    platform: Optional[str] = Query(default=None, description="meta,google,otro (uno o varios separados por coma)"),
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    cohort_desde: date = Query(default=None),
    cohort_hasta: date = Query(default=None),
    _: User = Depends(get_current_user),
):
    """Drill-down de quiénes pagaron — mismo patrón que
    /api/web-traffic/conversions y /whatsapp-conversions, con filtro de
    plataforma opcional (uno o varios buckets a la vez)."""
    desde, hasta = _default_range(desde, hasta)
    platforms = _parse_platforms(platform)
    if channel == "web":
        return get_web_conversions_detail(desde, hasta, platforms=platforms)
    return get_whatsapp_conversions_detail(desde, hasta, cohort_desde, cohort_hasta, platforms=platforms)
