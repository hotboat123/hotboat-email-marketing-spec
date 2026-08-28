"""
Recorre TODAS las firmas de terminos y condiciones (hotboat_signatures) y las
cruza con su reserva en all_appointments para crear/enriquecer el contacto con:
  - como_supieron (Instagram, Google, Tiktok, boca a boca...)
  - ciudad_origen -> location
  - categoria_cliente (familia / pareja / amigos)
  - tipo_cliente (trabajador / empresario)
  - ademas: nombre, telefono, cumpleanos, idioma, extras, ha_alojamiento, ticket_medio

Usa la misma logica de resolucion de booking_ref (AA-{id} / source_id / legacy)
que la automatizacion en produccion (app/services/automation_engine.py), pero
corre sobre las 139 firmas historicas sin la ventana de tiempo de 48h de esa
automatizacion, para que ninguna quede sin cruzar.

Ademas cruza cada firmante con los DEMAS firmantes de su misma reserva para
poblar contacts.companion_birthdays (cumpleanos de acompanantes conocidos,
para la automatizacion companion_birthday) -- salvo que la reserva tenga
emails duplicados entre firmantes o todos compartan la misma fecha de
nacimiento, senal de que una sola persona lleno el formulario por todos (ver
_companion_group_valid en automation_engine.py); esas reservas se saltan
como fuente de acompanantes y quedan marcadas en el log.

Seguro de re-ejecutar: solo agrega informacion, nunca borra datos existentes.

Uso:
  python enrich_contacts_from_signatures.py           # real
  python enrich_contacts_from_signatures.py --dry      # solo muestra cambios
"""
import os, sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:mcxQvhpGaatBzcZNCbVqnGWGBjQpCNYJ@turntable.proxy.rlwy.net:48129/railway")
os.environ.setdefault("SECRET_KEY", "d7d21f70d39dddea51376ab9c5d7f420c19a92d9322d2eb23e72faf97466892e")
os.environ.setdefault("RESEND_API_KEY", "x")

DRY = "--dry" in sys.argv

import time
from collections import defaultdict
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select
from app.models.contact import Contact
from app.services.automation_engine import (
    _resolve_appointment_from_booking_ref,
    _normalize_categoria_cliente,
    _normalize_tipo_cliente,
    _companion_group_valid,
    _companion_entries_for,
    _merge_companion_birthdays,
)

DB_URL = os.environ["DATABASE_URL"]
engine = create_engine(DB_URL)

print("Leyendo hotboat_signatures...")
with engine.connect() as conn:
    sigs = conn.execute(text("""
        SELECT id, booking_ref, passenger_name, passenger_email,
               passenger_phone, passenger_birthday
        FROM hotboat_signatures
        WHERE accepted_tc = true
          AND passenger_email IS NOT NULL
          AND passenger_email <> ''
        ORDER BY created_at
    """)).fetchall()

print(f"Firmas a procesar: {len(sigs)}")

by_booking = defaultdict(list)
for sig in sigs:
    by_booking[sig.booking_ref].append(sig)

skipped_bookings = {ref for ref, group in by_booking.items() if not _companion_group_valid(group)}
if skipped_bookings:
    print(f"Reservas saltadas como fuente de acompanantes (email o fecha duplicados): {len(skipped_bookings)}")
    for ref in sorted(skipped_bookings):
        print(f"  [SKIP companions] booking_ref={ref}")

created = updated = skipped = not_matched = 0
companions_added = 0


def _commit_with_retry(session, attempts=3):
    """The live production automation engine writes to the same `contacts`
    table continuously (every 60s) — a long batch transaction here can
    deadlock against it. Commit in small batches (see below) and retry once
    or twice on a transient Postgres deadlock instead of losing the whole
    run's progress."""
    for attempt in range(1, attempts + 1):
        try:
            session.commit()
            return
        except OperationalError as exc:
            session.rollback()
            if attempt == attempts or "deadlock" not in str(exc).lower():
                raise
            print(f"  [retry] deadlock on commit, attempt {attempt}/{attempts} — retrying...")
            time.sleep(2 * attempt)


with Session(engine) as session:
    for i, sig in enumerate(sigs):
        email = (sig.passenger_email or "").strip().lower()
        if not email or "@" not in email:
            skipped += 1
            continue

        sibling_sigs = by_booking[sig.booking_ref]
        new_companions = (
            _companion_entries_for(email, sibling_sigs)
            if sig.booking_ref not in skipped_bookings
            else []
        )

        appt = _resolve_appointment_from_booking_ref(sig.booking_ref, engine)
        if not appt:
            not_matched += 1

        ultima_visita = ticket_medio = location = language = extras = None
        ha_alojamiento = False
        como_supieron = categoria_cliente = tipo_cliente = None

        if appt:
            ultima_visita = appt.fecha
            if appt.ingreso_total:
                ticket_medio = float(appt.ingreso_total)
            location = (appt.ciudad_origen or "").strip() or None
            language = (appt.customer_language or "").strip() or None
            if appt.extras_json and isinstance(appt.extras_json, dict):
                extras = [k for k in appt.extras_json if not k.startswith("aloj__")] or None
                ha_alojamiento = any(k.startswith("aloj__") for k in appt.extras_json)
            como_supieron = (appt.como_supieron or "").strip() or None
            categoria_cliente = _normalize_categoria_cliente(appt.categoria_clientes)
            tipo_cliente = _normalize_tipo_cliente(appt.tipo_clientes)

        now_dt = datetime.utcnow()
        name = (sig.passenger_name or "").strip() or None
        phone = (sig.passenger_phone or "").strip() or None
        birthday = sig.passenger_birthday

        existing = session.exec(select(Contact).where(Contact.email == email)).first()

        if existing:
            changed = False
            if name and not existing.name:
                existing.name = name; changed = True
            if phone and not existing.phone:
                existing.phone = phone; changed = True
            if birthday and not existing.birthday:
                existing.birthday = birthday; changed = True
            if ultima_visita and (not existing.ultima_visita or ultima_visita > existing.ultima_visita):
                existing.ultima_visita = ultima_visita; changed = True
            if ticket_medio and not existing.ticket_medio:
                existing.ticket_medio = ticket_medio; changed = True
            if location and not existing.location:
                existing.location = location; changed = True
            if language and not existing.language:
                existing.language = language; changed = True
            if extras and not existing.extras_favoritos:
                existing.extras_favoritos = extras; changed = True
            if ha_alojamiento and not existing.ha_alojamiento:
                existing.ha_alojamiento = True; changed = True

            cf = dict(existing.custom_fields or {})
            if como_supieron and not cf.get("como_supieron"):
                cf["como_supieron"] = como_supieron; changed = True
            if categoria_cliente and not cf.get("categoria_cliente"):
                cf["categoria_cliente"] = categoria_cliente; changed = True
            if tipo_cliente and not cf.get("tipo_cliente"):
                cf["tipo_cliente"] = tipo_cliente; changed = True

            merged_companions, companions_changed = _merge_companion_birthdays(
                existing.companion_birthdays, new_companions
            )
            if companions_changed:
                changed = True
                companions_added += len(merged_companions) - len(existing.companion_birthdays or [])

            if changed:
                if DRY:
                    print(f"  [DRY update] {email} -> location={location} como_supieron={como_supieron} "
                          f"categoria={categoria_cliente} tipo={tipo_cliente} "
                          f"+companions={[c['name'] for c in new_companions] if companions_changed else []}")
                else:
                    existing.custom_fields = cf
                    if companions_changed:
                        existing.companion_birthdays = merged_companions
                    existing.updated_at = now_dt
                    session.add(existing)
                updated += 1
            else:
                skipped += 1
        else:
            cf = {}
            if como_supieron:
                cf["como_supieron"] = como_supieron
            if categoria_cliente:
                cf["categoria_cliente"] = categoria_cliente
            if tipo_cliente:
                cf["tipo_cliente"] = tipo_cliente

            if new_companions:
                companions_added += len(new_companions)

            if DRY:
                print(f"  [DRY create] {email} name={name} location={location} "
                      f"como_supieron={como_supieron} categoria={categoria_cliente} tipo={tipo_cliente} "
                      f"companions={[c['name'] for c in new_companions]}")
            else:
                contact = Contact(
                    email=email,
                    name=name,
                    phone=phone,
                    birthday=birthday,
                    language=language or "es",
                    origin_utm="Formulario T&C",
                    location=location,
                    custom_fields=cf or None,
                    companion_birthdays=new_companions or None,
                    opted_in=True,
                    opted_in_at=now_dt,
                    veces_hotboat=1 if appt else 0,
                    ultima_visita=ultima_visita,
                    ha_alojamiento=ha_alojamiento,
                    extras_favoritos=extras,
                    ticket_medio=ticket_medio,
                    created_at=now_dt,
                    updated_at=now_dt,
                )
                session.add(contact)
            created += 1

        if not DRY and (i + 1) % 20 == 0:
            _commit_with_retry(session)

    if not DRY:
        _commit_with_retry(session)

print()
print(f"Resultado: creados={created}  actualizados={updated}  sin_cambios={skipped}  sin_reserva_cruzada={not_matched}")
print(f"Acompanantes agregados (companion_birthdays): {companions_added}  "
      f"reservas saltadas por email/fecha duplicados: {len(skipped_bookings)}")
if DRY:
    print("(DRY RUN - no se escribio nada)")
