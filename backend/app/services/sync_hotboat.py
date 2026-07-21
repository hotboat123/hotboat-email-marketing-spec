"""
Sincroniza contactos desde las tablas fuente de HotBoat hacia la tabla contacts.

Fuentes:
  - all_appointments  → atributos derivados (veces_hotboat, ultima_visita, ticket_medio, etc.)
  - hotboat_signatures → pasajeros que firmaron términos y condiciones en el paseo — no
    siempre son la misma persona que reservó (viajes grupales: cada pasajero firma con
    su propio mail/teléfono/fecha de nacimiento), así que sin esto quedaban invisibles
    aunque sí vivieron la experiencia. Resuelto vía _fetch_signature_attendance() abajo.
  - accommodation_bookings → ha_alojamiento
  - extras_bookings   → extras_favoritos
  - leads → datos base de contacto
"""
import json
import logging
from datetime import date, datetime
from typing import Optional
from sqlalchemy import create_engine, text
from sqlmodel import Session, select
from app.core.config import settings
from app.models.contact import Contact

logger = logging.getLogger(__name__)


def _source_engine():
    url = settings.HOTBOAT_DATABASE_URL or settings.DATABASE_URL
    return create_engine(url)


_ACTIVE_STATUS_FILTER = "aa.status NOT IN ('cancelled', 'no_show', 'pending')"

_BOOKING_COLUMNS = """
    aa.id, aa.appointment_id, aa.fecha, aa.hora, aa.servicio, aa.num_personas,
    aa.observaciones, aa.extras_json, aa.ingreso_total, aa.status
"""


def _fetch_signature_attendance(conn) -> list:
    """One row per (passenger_email, booking) a signed passenger actually
    attended, resolved from hotboat_signatures.booking_ref — either 'AA-{id}'
    (all_appointments.id) or the appointment_id string directly. Returns raw
    rows; aggregation happens in Python alongside the direct-booker rows so
    veces_hotboat/extras/etc. never double-count a booking seen from both
    angles (the booker signing for themselves, e.g.)."""
    return conn.execute(text(f"""
        WITH resolved AS (
            SELECT hs.passenger_email, hs.passenger_name, hs.passenger_phone,
                   hs.passenger_birthday, hs.created_at,
                   CASE WHEN hs.booking_ref ILIKE 'AA-%' THEN
                       NULLIF(substring(hs.booking_ref from 4), '')::int
                   END AS apt_pk,
                   CASE WHEN hs.booking_ref NOT ILIKE 'AA-%' THEN hs.booking_ref END AS apt_ref
            FROM hotboat_signatures hs
            WHERE hs.passenger_email IS NOT NULL AND hs.passenger_email <> ''
        )
        SELECT r.passenger_email, r.passenger_name, r.passenger_phone, r.passenger_birthday,
               {_BOOKING_COLUMNS}
        FROM resolved r
        JOIN all_appointments aa
          ON (r.apt_pk IS NOT NULL AND aa.id = r.apt_pk)
          OR (r.apt_ref IS NOT NULL AND aa.appointment_id = r.apt_ref)
        WHERE {_ACTIVE_STATUS_FILTER}
    """)).fetchall()


def _extras_dict(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


def _booking_summary(row) -> dict:
    """The "objeto asociado a su reserva" — extras, observaciones, etc. —
    stored on the contact so the team can see what a signed passenger's trip
    actually included, not just that they showed up."""
    extras = {k: v for k, v in _extras_dict(row.extras_json).items() if not k.startswith("aloj__")}
    return {
        "booking_ref": row.appointment_id or f"AA-{row.id}",
        "fecha": str(row.fecha) if row.fecha else None,
        "hora": str(row.hora)[:5] if row.hora else None,
        "servicio": row.servicio,
        "num_personas": row.num_personas,
        "observaciones": row.observaciones,
        "extras": extras,
        "ingreso_total": float(row.ingreso_total) if row.ingreso_total else None,
    }


def sync_contacts(session: Session) -> dict:
    engine = _source_engine()

    with engine.connect() as conn:
        # ── 1. Reservas directas desde all_appointments (una fila por reserva,
        #      no agregada — se agrega en Python junto con las firmas para no
        #      contar dos veces la misma reserva cuando la misma persona
        #      reservó Y firmó) ──────────────────────────────────────────────
        booker_rows = conn.execute(text(f"""
            SELECT
                aa.email, aa.nombre_cliente AS name, aa.telefono AS phone,
                aa.customer_language AS language, aa.como_supieron AS origin_utm,
                aa.ciudad_origen AS location, NULL::date AS birthday,
                {_BOOKING_COLUMNS}
            FROM all_appointments aa
            WHERE aa.email IS NOT NULL AND aa.email <> ''
              AND {_ACTIVE_STATUS_FILTER}
        """)).fetchall()

        # ── 1b. Asistencia vía firma de T&C (puede ser gente distinta a quien
        #        reservó — viajes grupales, cada pasajero firma por su cuenta) ──
        signature_rows = _fetch_signature_attendance(conn)

        # ── Agregar ambas fuentes por email, deduplicando por reserva (aa.id) ──
        attendance: dict[str, dict] = {}
        for src_rows, is_signature in ((booker_rows, False), (signature_rows, True)):
            for r in src_rows:
                email = (r.passenger_email if is_signature else r.email) or ""
                email = email.lower().strip()
                if not email:
                    continue
                a = attendance.setdefault(email, {
                    "booking_ids": set(), "bookings": {}, "name": None, "phone": None,
                    "language": None, "origin_utm": None, "location": None, "birthday": None,
                })
                a["booking_ids"].add(r.id)
                a["bookings"][r.id] = r  # last writer wins per booking; fine, same row either way
                # Prefer values from whichever source has them — direct-booker
                # row usually carries language/origin_utm/location; signature
                # rows are the only source for birthday.
                name = r.passenger_name if is_signature else r.name
                phone = r.passenger_phone if is_signature else r.phone
                if name and not a["name"]:
                    a["name"] = name
                if phone and not a["phone"]:
                    a["phone"] = phone
                if not is_signature:
                    if r.language and not a["language"]:
                        a["language"] = r.language
                    if r.origin_utm and not a["origin_utm"]:
                        a["origin_utm"] = r.origin_utm
                    if r.location and not a["location"]:
                        a["location"] = r.location
                if is_signature and r.passenger_birthday and not a["birthday"]:
                    a["birthday"] = r.passenger_birthday

        # ── 2. Emails con alojamiento (accommodation_bookings + extras_json con aloj__) ──
        accom_emails = {
            r[0].lower().strip()
            for r in conn.execute(text("""
                SELECT DISTINCT customer_email
                FROM accommodation_bookings
                WHERE customer_email IS NOT NULL AND status NOT IN ('cancelled')
                UNION
                SELECT DISTINCT email
                FROM all_appointments,
                     jsonb_object_keys(extras_json) AS key
                WHERE email IS NOT NULL AND email <> ''
                  AND jsonb_typeof(extras_json) = 'object'
                  AND key LIKE 'aloj__%'
            """)).fetchall()
            if r[0]
        }

        # ── 4. Leads como fuente secundaria de emails ─────────────────────────────
        # (booknetic_customers se dio de baja — el plugin Booknetic de WordPress
        # ya no se usa, todas las reservas pasan por el sistema propio de HotBoat)
        extra_contacts: dict[str, dict] = {}
        for r in conn.execute(text("""
            SELECT email, name, phone FROM leads
            WHERE email IS NOT NULL AND email <> ''
        """)).fetchall():
            em = r[0].lower().strip()
            if em not in extra_contacts:
                extra_contacts[em] = {"name": r[1], "phone": r[2]}

        location_by_email: dict[str, str] = {}

    # ── Upsert en nuestra tabla contacts ────────────────────────────────────────
    created = updated = skipped = 0

    for email, a in attendance.items():
        if not email:
            skipped += 1
            continue

        existing = session.exec(select(Contact).where(Contact.email == email)).first()
        name     = (a["name"] or extra_contacts.get(email, {}).get("name") or "").strip() or None
        phone    = (a["phone"] or extra_contacts.get(email, {}).get("phone") or "").strip() or None
        language = _normalize_language(a["language"])
        ha_aloj  = email in accom_emails
        location = (a["location"] or "").strip() or location_by_email.get(email) or None
        birthday = a["birthday"]

        bookings = list(a["bookings"].values())
        veces_hotboat = len(a["booking_ids"])
        fechas = [b.fecha for b in bookings if b.fecha]
        ultima_visita = max(fechas) if fechas else None
        ingresos = [float(b.ingreso_total) for b in bookings if b.ingreso_total]
        ticket_medio = round(sum(ingresos) / len(ingresos)) if ingresos else None

        extras_set: set = set()
        for b in bookings:
            extras_set.update(k for k in _extras_dict(b.extras_json) if not k.startswith("aloj__"))
        extras = sorted(extras_set) or None

        latest_booking = max(bookings, key=lambda b: (b.fecha or date.min, b.id)) if bookings else None
        booking_summary = _booking_summary(latest_booking) if latest_booking else None

        if existing:
            existing.name             = name or existing.name
            existing.phone            = phone or existing.phone
            existing.language         = language or existing.language
            existing.origin_utm       = a["origin_utm"] or existing.origin_utm
            existing.location         = location or existing.location
            existing.veces_hotboat    = veces_hotboat
            existing.ultima_visita    = ultima_visita
            existing.ha_alojamiento   = ha_aloj
            existing.extras_favoritos = extras
            existing.ticket_medio     = ticket_medio if ticket_medio is not None else existing.ticket_medio
            existing.birthday         = existing.birthday or birthday
            if booking_summary:
                existing.ultima_reserva_hotboat = booking_summary
            existing.updated_at       = datetime.utcnow()
            session.add(existing)
            updated += 1
        else:
            contact = Contact(
                email             = email,
                name              = name,
                phone             = phone,
                language          = language,
                origin_utm        = a["origin_utm"],
                location          = location,
                opted_in          = True,
                opted_in_at       = datetime.utcnow(),
                veces_hotboat     = veces_hotboat,
                ultima_visita     = ultima_visita,
                ha_alojamiento    = ha_aloj,
                extras_favoritos  = extras,
                ticket_medio      = ticket_medio,
                birthday          = birthday,
                ultima_reserva_hotboat = booking_summary,
            )
            session.add(contact)
            created += 1

    # Contactos de booknetic/leads que no tienen appointments
    for email, data in extra_contacts.items():
        if session.exec(select(Contact).where(Contact.email == email)).first():
            continue
        session.add(Contact(
            email       = email,
            name        = (data.get("name") or "").strip() or None,
            phone       = (data.get("phone") or "").strip() or None,
            opted_in    = True,
            opted_in_at = datetime.utcnow(),
        ))
        created += 1

    session.commit()

    result = {"created": created, "updated": updated, "skipped": skipped}
    logger.info("Sync completado: %s", result)
    return result


def _normalize_language(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = raw.lower().strip()
    if raw in ("es", "español", "spanish", "castellano"):
        return "es"
    if raw in ("en", "english", "inglés", "ingles"):
        return "en"
    return raw[:5] if raw else None
