"""
Import T&C sign-ups from a Google Form CSV export.

For each attendee (including companions who didn't make the booking):
  1. Resolve the best email from the 3 possible email columns.
  2. Parse Marca temporal (DD/MM/YYYY HH:MM:SS).
  3. Find a matching appointment in all_appointments where fecha+hora is
     within ±1 hour of the timestamp.  If multiple candidates exist, prefer
     the one whose nombre_cliente contains a word from the reservation holder
     name; fall back to closest timestamp.
  4. Enrich the contact with booking data: extras, alojamiento, ticket_medio,
     ultima_visita, language, location.
  5. Upsert into contacts with opted_in=True.
"""
import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import create_engine, text
from sqlmodel import Session, select

from app.core.config import settings
from app.models.contact import Contact

logger = logging.getLogger(__name__)

# CSV column names from Google Forms export
_COL_TS       = "Marca temporal"
_COL_NAME     = "Nombre"
_COL_BDAY     = "Fecha de nacimiento"
_COL_EMAIL1   = "Email"
_COL_EMAIL2   = "Dirección de correo electrónico"
_COL_EMAIL3   = "email (si iniciaste sesión puedes dejarlo vacio)"
_COL_PHONE    = "Teléfono"
_COL_ACCEPTED = "Acepto Términos y Condiciones\nI Accept Terms and Conditions"
_COL_HOLDER   = "¿A nombre de quién está la reserva?"


def _source_engine():
    url = settings.HOTBOAT_DATABASE_URL or settings.DATABASE_URL
    return create_engine(url)


def _best_email(row: dict) -> Optional[str]:
    for col in [_COL_EMAIL2, _COL_EMAIL3, _COL_EMAIL1]:
        val = (row.get(col) or "").strip().lower()
        if val and "@" in val:
            return val
    return None


def _parse_ts(raw: str) -> Optional[datetime]:
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_date(raw: str) -> Optional[object]:
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _normalize(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _name_score(appt_name: str, holder: str) -> int:
    """Return number of significant words (>2 chars) in holder that appear in appt_name."""
    an = _normalize(appt_name)
    return sum(1 for w in _normalize(holder).split() if len(w) > 2 and w in an)


def import_tc_csv(content: bytes, session: Session) -> dict:
    src = _source_engine()
    text_io = io.StringIO(content.decode("utf-8-sig"))
    reader = csv.DictReader(text_io)

    created = updated = skipped = 0
    no_appointment_match = 0

    with src.connect() as conn:
        for row in reader:
            email = _best_email(row)
            if not email:
                skipped += 1
                continue

            accepted = _normalize(row.get(_COL_ACCEPTED) or "")
            if accepted not in ("sí", "si", "yes"):
                skipped += 1
                continue

            ts = _parse_ts(row.get(_COL_TS) or "")
            if not ts:
                skipped += 1
                continue

            holder = row.get(_COL_HOLDER) or ""
            name   = (row.get(_COL_NAME) or "").strip() or None
            phone  = (row.get(_COL_PHONE) or "").strip() or None
            birthday = _parse_date(row.get(_COL_BDAY) or "")

            # ── Match appointment ───────────────────────────────────────────
            appt = None
            try:
                ws = ts - timedelta(hours=1)
                we = ts + timedelta(hours=1)

                candidates = conn.execute(text("""
                    SELECT nombre_cliente, servicio, fecha, hora,
                           num_adultos, num_ninos, ingreso_total,
                           extras_json, customer_language,
                           ciudad_origen, telefono, como_supieron
                    FROM all_appointments
                    WHERE (fecha + COALESCE(hora, '12:00:00'::time)) >= :ws
                      AND (fecha + COALESCE(hora, '12:00:00'::time)) <= :we
                      AND status NOT IN ('cancelled', 'no_show', 'pending_payment')
                    ORDER BY ABS(EXTRACT(EPOCH FROM
                        ((fecha + COALESCE(hora, '12:00:00'::time)) - :ts)))
                    LIMIT 10
                """), {"ws": ws, "we": we, "ts": ts}).fetchall()

                if candidates:
                    if holder:
                        best = max(candidates, key=lambda c: _name_score(c.nombre_cliente or "", holder))
                        if _name_score(best.nombre_cliente or "", holder) > 0:
                            appt = best
                    if appt is None:
                        appt = candidates[0]
                else:
                    no_appointment_match += 1
            except Exception as exc:
                logger.warning("TC import: appointment lookup failed for %s: %s", email, exc)
                no_appointment_match += 1

            # ── Extract enrichment from appointment ─────────────────────────
            ultima_visita  = None
            ticket_medio   = None
            location       = None
            language       = None
            extras         = None
            ha_alojamiento = False
            origin         = "Formulario T&C"

            if appt:
                ultima_visita = appt.fecha
                if appt.ingreso_total:
                    ticket_medio = float(appt.ingreso_total)
                location = (appt.ciudad_origen or "").strip() or None
                language = (appt.customer_language or "").strip() or None
                origin   = (appt.como_supieron or "").strip() or "Formulario T&C"
                if appt.extras_json and isinstance(appt.extras_json, dict):
                    extras = [k for k in appt.extras_json if not k.startswith("aloj__")] or None
                    ha_alojamiento = any(k.startswith("aloj__") for k in appt.extras_json)

            # ── Upsert contact ───────────────────────────────────────────────
            now = datetime.utcnow()
            existing = session.exec(select(Contact).where(Contact.email == email)).first()

            if existing:
                if name and not existing.name:
                    existing.name = name
                if phone and not existing.phone:
                    existing.phone = phone
                if birthday and not existing.birthday:
                    existing.birthday = birthday
                if ultima_visita and (not existing.ultima_visita or ultima_visita > existing.ultima_visita):
                    existing.ultima_visita = ultima_visita
                if ticket_medio and not existing.ticket_medio:
                    existing.ticket_medio = ticket_medio
                if location and not existing.location:
                    existing.location = location
                if language and not existing.language:
                    existing.language = language
                if extras and not existing.extras_favoritos:
                    existing.extras_favoritos = extras
                if ha_alojamiento:
                    existing.ha_alojamiento = True
                existing.opted_in = True
                if not existing.opted_in_at:
                    existing.opted_in_at = now
                existing.updated_at = now
                session.add(existing)
                updated += 1
            else:
                session.add(Contact(
                    email          = email,
                    name           = name,
                    phone          = phone,
                    birthday       = birthday,
                    language       = language,
                    origin_utm     = origin,
                    location       = location,
                    opted_in       = True,
                    opted_in_at    = now,
                    veces_hotboat  = 1 if appt else 0,
                    ultima_visita  = ultima_visita,
                    ha_alojamiento = ha_alojamiento,
                    extras_favoritos = extras,
                    ticket_medio   = ticket_medio,
                ))
                created += 1

    session.commit()
    result = {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "no_appointment_match": no_appointment_match,
    }
    logger.info("TC import: %s", result)
    return result
