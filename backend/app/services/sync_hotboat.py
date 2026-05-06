"""
Sincroniza contactos desde las tablas fuente de HotBoat hacia la tabla contacts.

Fuentes:
  - all_appointments  → atributos derivados (veces_hotboat, ultima_visita, ticket_medio, etc.)
  - accommodation_bookings → ha_alojamiento
  - extras_bookings   → extras_favoritos
  - booknetic_customers + leads → datos base de contacto
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, text
from sqlmodel import Session, select
from app.core.config import settings
from app.models.contact import Contact

logger = logging.getLogger(__name__)


def _source_engine():
    url = settings.HOTBOAT_DATABASE_URL or settings.DATABASE_URL
    return create_engine(url)


def sync_contacts(session: Session) -> dict:
    engine = _source_engine()

    with engine.connect() as conn:
        # ── 1. Datos base + atributos derivados desde all_appointments ──────────
        rows = conn.execute(text("""
            SELECT
                aa.email,
                MAX(aa.nombre_cliente)                          AS name,
                MAX(aa.telefono)                                AS phone,
                MAX(aa.customer_language)                       AS language,
                MAX(aa.como_supieron)                           AS origin_utm,
                COUNT(*)                                        AS veces_hotboat,
                MAX(aa.fecha)                                   AS ultima_visita,
                ROUND(AVG(aa.ingreso_total)::numeric, 0)        AS ticket_medio
            FROM all_appointments aa
            WHERE aa.email IS NOT NULL
              AND aa.email <> ''
              AND aa.status NOT IN ('cancelled', 'no_show', 'pending')
            GROUP BY aa.email
        """)).fetchall()

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

        # ── 3. Extras favoritos desde all_appointments.extras_json ──────────────
        extras_by_email: dict[str, list[str]] = {}
        for r in conn.execute(text("""
            SELECT email, array_agg(DISTINCT key) AS extras
            FROM all_appointments,
                 jsonb_object_keys(extras_json) AS key
            WHERE email IS NOT NULL AND email <> ''
              AND extras_json IS NOT NULL AND extras_json <> '{}'
              AND jsonb_typeof(extras_json) = 'object'
              AND key NOT LIKE 'aloj__%'
            GROUP BY email
        """)).fetchall():
            em = r[0].lower().strip()
            extras_by_email[em] = [s for s in (r[1] or []) if s]

        # ── 4. Leads y booknetic_customers como fuente secundaria de emails ──────
        extra_contacts: dict[str, dict] = {}
        for r in conn.execute(text("""
            SELECT email, name, phone FROM booknetic_customers
            WHERE email IS NOT NULL AND email <> ''
            UNION
            SELECT email, name, phone FROM leads
            WHERE email IS NOT NULL AND email <> ''
        """)).fetchall():
            em = r[0].lower().strip()
            if em not in extra_contacts:
                extra_contacts[em] = {"name": r[1], "phone": r[2]}

        # ── 5. Ubicación desde booknetic_customers (si la columna existe) ────────
        location_by_email: dict[str, str] = {}
        try:
            loc_rows = conn.execute(text("""
                SELECT email,
                       COALESCE(city, '') || CASE WHEN city IS NOT NULL AND state IS NOT NULL THEN ', ' ELSE '' END
                       || COALESCE(state, '') AS location
                FROM booknetic_customers
                WHERE email IS NOT NULL AND email <> ''
                  AND (city IS NOT NULL OR state IS NOT NULL)
            """)).fetchall()
            for r in loc_rows:
                em = r[0].lower().strip()
                loc = (r[1] or "").strip()
                if loc:
                    location_by_email[em] = loc
        except Exception:
            # booknetic_customers doesn't have city/state columns — skip silently
            pass

    # ── Upsert en nuestra tabla contacts ────────────────────────────────────────
    created = updated = skipped = 0

    for row in rows:
        email = row.email.lower().strip() if row.email else None
        if not email:
            skipped += 1
            continue

        existing = session.exec(select(Contact).where(Contact.email == email)).first()
        name     = (row.name or extra_contacts.get(email, {}).get("name") or "").strip() or None
        phone    = (row.phone or extra_contacts.get(email, {}).get("phone") or "").strip() or None
        language = _normalize_language(row.language)
        ha_aloj  = email in accom_emails
        extras   = extras_by_email.get(email) or None
        location = location_by_email.get(email) or None

        if existing:
            existing.name             = name or existing.name
            existing.phone            = phone or existing.phone
            existing.language         = language or existing.language
            existing.origin_utm       = row.origin_utm or existing.origin_utm
            existing.location         = location or existing.location
            existing.veces_hotboat    = int(row.veces_hotboat)
            existing.ultima_visita    = row.ultima_visita
            existing.ha_alojamiento   = ha_aloj
            existing.extras_favoritos = extras
            existing.ticket_medio     = float(row.ticket_medio) if row.ticket_medio else existing.ticket_medio
            existing.updated_at       = datetime.utcnow()
            session.add(existing)
            updated += 1
        else:
            contact = Contact(
                email             = email,
                name              = name,
                phone             = phone,
                language          = language,
                origin_utm        = row.origin_utm,
                location          = location,
                opted_in          = True,
                opted_in_at       = datetime.utcnow(),
                veces_hotboat     = int(row.veces_hotboat),
                ultima_visita     = row.ultima_visita,
                ha_alojamiento    = ha_aloj,
                extras_favoritos  = extras,
                ticket_medio      = float(row.ticket_medio) if row.ticket_medio else None,
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
