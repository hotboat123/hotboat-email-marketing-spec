"""
Manual overrides for a reservation's attribution (fuente/flujo) — an
operator correcting a wrongly-classified booking straight from the
"Quiénes pagaron" drill-down modal (ConversionsModal, shared by both the
Web and WhatsApp conversion lists in Tráfico Web).

Both fuente ("meta"/"google"/"otro" — see platform_attribution.py's
bucket_3) and flujo ("flujo_1"/"flujo_2"/"flujo_3" — see
PHONE_FLUJO_LATERAL in web_traffic_analytics.py) are normally COMPUTED on
every read from contacts_crm.platform / booking_visitor_events history.
These two override columns on all_appointments let a human pin an exact
value instead — get_web_conversions_detail/get_whatsapp_conversions_detail
COALESCE them over the computed value. NULL (the default) means "still
computed automatically", not "unknown".
"""
from sqlalchemy import text

FUENTE_VALUES = {"meta", "google", "otro"}
FLUJO_VALUES = {"flujo_1", "flujo_2", "flujo_3"}

_override_columns_ensured = False


def _ensure_override_columns(engine) -> None:
    """Runs once per process — same self-migrating pattern as
    contacts.py's attach_booking (CREATE TABLE IF NOT EXISTS inline),
    just ADD COLUMN instead since all_appointments already exists."""
    global _override_columns_ensured
    if _override_columns_ensured:
        return
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE all_appointments ADD COLUMN IF NOT EXISTS fuente_override TEXT"))
        conn.execute(text("ALTER TABLE all_appointments ADD COLUMN IF NOT EXISTS flujo_override TEXT"))
        conn.commit()
    _override_columns_ensured = True


def set_appointment_overrides(
    appointment_pk: int,
    fuente: str | None = ...,
    flujo: str | None = ...,
) -> None:
    """Updates fuente_override and/or flujo_override for
    all_appointments.id = appointment_pk. Pass `...` (the default) for
    whichever one you don't want to touch — None means "clear the
    override, go back to automatic". Raises ValueError on an
    out-of-vocabulary value (never silently drops a typo'd value)."""
    if fuente is not ... and fuente is not None and fuente not in FUENTE_VALUES:
        raise ValueError(f"fuente inválida: {fuente!r} (debe ser una de {sorted(FUENTE_VALUES)})")
    if flujo is not ... and flujo is not None and flujo not in FLUJO_VALUES:
        raise ValueError(f"flujo inválido: {flujo!r} (debe ser una de {sorted(FLUJO_VALUES)})")

    sets, params = [], {"id": appointment_pk}
    if fuente is not ...:
        sets.append("fuente_override = :fuente")
        params["fuente"] = fuente
    if flujo is not ...:
        sets.append("flujo_override = :flujo")
        params["flujo"] = flujo
    if not sets:
        return

    from app.services.web_traffic_analytics import _source_engine
    engine = _source_engine()
    _ensure_override_columns(engine)
    with engine.connect() as conn:
        result = conn.execute(
            text(f"UPDATE all_appointments SET {', '.join(sets)} WHERE id = :id"),
            params,
        )
        conn.commit()
        if result.rowcount == 0:
            raise LookupError(f"No existe all_appointments.id = {appointment_pk}")
