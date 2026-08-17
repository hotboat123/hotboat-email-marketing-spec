from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from app.core.deps import get_current_user, require_editor
from app.models.user import User
from app.services.web_traffic_analytics import (
    get_web_traffic_daily, get_session_duration_histogram, get_web_conversions_detail,
)
from app.services.whatsapp_traffic_analytics import (
    get_whatsapp_traffic_daily, get_whatsapp_conversions_detail, list_bot_variants,
)
from app.services.appointment_overrides import set_appointment_overrides

router = APIRouter()


def _default_range(desde: date, hasta: date) -> tuple[date, date]:
    if hasta is None:
        hasta = date.today()
    if desde is None:
        desde = hasta - timedelta(days=61)  # ~2 meses por defecto
    return desde, hasta


def _parse_bot_variants(bot_variant: Optional[str]) -> Optional[list[str]]:
    """`bot_variant` acepta una sola variante o varias separadas por coma
    (ej. "control,ia_1") — filtro multi-select, mismo patrón que
    `platform` en sources.py. Sin validación contra un catálogo fijo (a
    diferencia de plataforma): las variantes son texto libre, definidas
    por el dueño en bot_ab_variants y pueden crecer con el tiempo (ver
    list_bot_variants) — una variante inválida/vieja simplemente no
    matchea ninguna fila."""
    if not bot_variant:
        return None
    values = [v.strip() for v in bot_variant.split(",") if v.strip()]
    return values or None


@router.get("/bot-variants")
def bot_variants(_: User = Depends(get_current_user)):
    """Catálogo de variantes de bot (control/ia_1/...) para el selector de
    filtro — ver list_bot_variants()."""
    return list_bot_variants()


@router.get("/daily")
def web_traffic_daily(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    bot_variant: Optional[str] = Query(default=None, description="variant_key (uno o varios separados por coma) — filtra solo el conteo de pagos, ver get_web_traffic_daily"),
    _: User = Depends(get_current_user),
):
    """Tráfico diario del sitio (landing hotboat.cl + booking-soft.html) —
    ver app/services/web_traffic_analytics.py para las definiciones exactas
    de cada métrica (sesión útil, "encontró caro", conversión, etc.)."""
    desde, hasta = _default_range(desde, hasta)
    return get_web_traffic_daily(desde, hasta, bot_variants=_parse_bot_variants(bot_variant))


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
    bot_variant: Optional[str] = Query(default=None, description="variant_key (uno o varios separados por coma)"),
    _: User = Depends(get_current_user),
):
    """Tráfico diario de WhatsApp — ver app/services/whatsapp_traffic_analytics.py
    para las definiciones exactas (conversación útil, "encontró caro", etc.)."""
    desde, hasta = _default_range(desde, hasta)
    return get_whatsapp_traffic_daily(desde, hasta, bot_variants=_parse_bot_variants(bot_variant))


@router.get("/conversions")
def web_conversions_detail(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    bot_variant: Optional[str] = Query(default=None, description="variant_key (uno o varios separados por coma)"),
    _: User = Depends(get_current_user),
):
    """Quiénes son los "paid" de la pestaña web — mismo criterio y mismo
    número que la tarjeta de conversión."""
    desde, hasta = _default_range(desde, hasta)
    return get_web_conversions_detail(desde, hasta, bot_variants=_parse_bot_variants(bot_variant))


@router.get("/whatsapp-conversions")
def whatsapp_conversions_detail(
    desde: date = Query(default=None),
    hasta: date = Query(default=None),
    cohort_desde: date = Query(default=None),
    cohort_hasta: date = Query(default=None),
    bot_variant: Optional[str] = Query(default=None, description="variant_key (uno o varios separados por coma)"),
    _: User = Depends(get_current_user),
):
    """Quiénes son los "paid" de la pestaña WhatsApp, con clasificación por
    orden cronológico (flujo 1 vs flujo 3) — ver
    get_whatsapp_conversions_detail() para el criterio exacto.

    desde/hasta siguen siendo el rango completo elegido en la página (para
    que el "día de cohorte" de cada teléfono se calcule igual que en la
    agregada). cohort_desde/cohort_hasta son opcionales y acotan el
    resultado a un día o bucket puntual del gráfico, sin cambiar ese
    cálculo — ver el docstring de get_whatsapp_conversions_detail()."""
    desde, hasta = _default_range(desde, hasta)
    return get_whatsapp_conversions_detail(
        desde, hasta, cohort_desde, cohort_hasta, bot_variants=_parse_bot_variants(bot_variant),
    )


class ConversionOverridesPayload(BaseModel):
    # A field left OUT of the request body entirely leaves that override
    # untouched (see exclude_unset=True below) — sending it as null clears
    # the override back to automatic, sending a real value pins it. See
    # set_appointment_overrides() for the vocab check.
    fuente: Optional[str] = None
    flujo: Optional[str] = None

    model_config = {"extra": "forbid"}


@router.patch("/conversions/{appointment_id}/overrides")
def set_conversion_overrides(
    appointment_id: int,
    payload: ConversionOverridesPayload,
    _: User = Depends(require_editor),
):
    """Corrige a mano la fuente y/o el flujo de una reserva puntual, desde
    el modal "Quiénes pagaron" (ConversionsModal, compartido por las listas
    Web y WhatsApp) — ver app/services/appointment_overrides.py. Un campo
    omitido del body no se toca; enviarlo en null borra el override
    (vuelve a calcularse automático)."""
    fields = payload.model_dump(exclude_unset=True)
    try:
        set_appointment_overrides(
            appointment_id,
            fuente=fields.get("fuente", ...),
            flujo=fields.get("flujo", ...),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}
