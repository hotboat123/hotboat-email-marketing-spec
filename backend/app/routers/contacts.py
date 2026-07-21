import csv
import io
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import create_engine, text
from sqlmodel import Session, select
import resend
from app.database import get_session
from app.core.config import settings
from app.core.deps import get_current_user, require_editor
from app.core.unsub_token import verify_unsub_token
from app.models.user import User
from app.models.contact import Contact, ContactCreate, ContactRead, ContactUpdate
from app.models.campaign import Campaign, CampaignSend
from app.models.automation import AutomationRun
from app.models.segment import Segment
from app.services.segment_evaluator import _build_clause

logger = logging.getLogger(__name__)

router = APIRouter()


def _hotboat_engine():
    """Engine hacia la DB fuente de HotBoat, con timeout de conexión corto —
    sin esto, un problema de red deja el request colgado indefinidamente en
    vez de fallar rápido (esta DB es compartida con el sistema de reservas
    en vivo, así que un connect() colgado no debe acumularse request tras
    request)."""
    src_url = settings.HOTBOAT_DATABASE_URL or settings.DATABASE_URL
    return create_engine(src_url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)


@router.get("", response_model=List[ContactRead])
def list_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    search: Optional[str] = None,
    opted_in: Optional[bool] = None,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    query = select(Contact)
    if search:
        query = query.where(
            Contact.email.ilike(f"%{search}%") | Contact.name.ilike(f"%{search}%")
        )
    if opted_in is not None:
        query = query.where(Contact.opted_in == opted_in)
    query = query.offset(skip).limit(limit)
    return session.exec(query).all()


@router.get("/count")
def count_contacts(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return {"count": session.exec(select(Contact)).all().__len__()}


def _do_unsubscribe(email: str, session: Session) -> None:
    contact = session.exec(select(Contact).where(Contact.email == email.lower())).first()
    if contact and contact.opted_in:
        contact.opted_in = False
        contact.opted_out_at = datetime.utcnow()
        session.add(contact)
        session.commit()
        _notify_unsubscribe(contact)


def _notify_unsubscribe(contact: Contact) -> None:
    if not settings.NOTIFY_EMAIL:
        return
    try:
        resend.api_key = settings.RESEND_API_KEY
        name = contact.name or contact.email
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [settings.NOTIFY_EMAIL],
            "subject": f"Desuscripción: {name}",
            "html": (
                f"<p><strong>{name}</strong> ({contact.email}) "
                f"se ha dado de baja de la lista de HotBoat.</p>"
                f"<p style='color:#999;font-size:13px;'>Puedes ver su perfil en "
                f"<a href='{settings.FRONTEND_URL}/contacts/{contact.id}'>el panel</a>.</p>"
            ),
        })
    except Exception as exc:
        logger.warning("No se pudo enviar notificación de desuscripción: %s", exc)


@router.get("/unsubscribe")
def unsubscribe_get(email: str = Query(...), token: str = Query(...), session: Session = Depends(get_session)):
    """Enlace de baja desde el cuerpo del email (click del usuario)."""
    if not verify_unsub_token(email, token):
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    _do_unsubscribe(email, session)
    return {"ok": True}


@router.post("/unsubscribe")
def unsubscribe_one_click(email: str = Query(...), token: str = Query(...), session: Session = Depends(get_session)):
    """One-click unsubscribe para clientes de email (Gmail List-Unsubscribe-Post)."""
    if not verify_unsub_token(email, token):
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    _do_unsubscribe(email, session)
    return {"ok": True}


@router.post("", response_model=ContactRead, status_code=201)
def create_contact(
    payload: ContactCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    existing = session.exec(select(Contact).where(Contact.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ya existe")
    contact = Contact(**payload.model_dump(), opted_in_at=datetime.utcnow() if payload.opted_in else None)
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact


@router.get("/available-bookings")
def available_bookings(
    date: str = Query(..., description="YYYY-MM-DD"),
    _: User = Depends(get_current_user),
):
    """Reservas de HotBoat en una fecha dada, para elegir a cuál asociar un
    contacto como pasajero que firmó los T&C (ver /contacts/{id}/attach_booking).
    Registrada antes de /{contact_id} a propósito — de lo contrario ese path
    dinámico se la come primero y devuelve 422 (contact_id inválido)."""
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido, usa YYYY-MM-DD")

    engine = _hotboat_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, nombre_cliente, hora, num_personas, source, source_id
                FROM all_appointments
                WHERE fecha = :date
                  AND status NOT IN ('cancelled', 'cancelada')
                ORDER BY hora ASC NULLS LAST
            """), {"date": target}).fetchall()
    except Exception:
        return []
    finally:
        engine.dispose()

    out = []
    for r in rows:
        booking_ref = r.source_id if r.source == "hotboat_web" and r.source_id else f"AA-{r.id}"
        out.append({
            "booking_ref": booking_ref,
            "nombre_cliente": r.nombre_cliente or "Sin nombre",
            "hora": str(r.hora)[:5] if r.hora else None,
            "num_personas": r.num_personas,
        })
    return out


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: int, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return contact


@router.patch("/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: int,
    payload: ContactUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "opted_in" in data:
        if data["opted_in"] and not contact.opted_in:
            contact.opted_in_at = datetime.utcnow()
            contact.opted_out_at = None
        elif not data["opted_in"] and contact.opted_in:
            contact.opted_out_at = datetime.utcnow()
    for k, v in data.items():
        setattr(contact, k, v)
    contact.updated_at = datetime.utcnow()
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    # Delete FK-referencing rows first to avoid constraint violations
    for row in session.exec(select(CampaignSend).where(CampaignSend.contact_id == contact_id)).all():
        session.delete(row)
    for row in session.exec(select(AutomationRun).where(AutomationRun.contact_id == contact_id)).all():
        session.delete(row)
    session.delete(contact)
    session.commit()


@router.get("/{contact_id}/segments")
def contact_segments(
    contact_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Devuelve los segmentos a los que pertenece el contacto."""
    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    all_segs = session.exec(select(Segment)).all()
    matching = []
    for seg in all_segs:
        q = select(Contact).where(Contact.id == contact_id, Contact.opted_in == True)  # noqa: E712
        if seg.conditions:
            clause = _build_clause(seg.conditions)
            if clause is not None:
                q = q.where(clause)
        if session.exec(q).first():
            matching.append({"id": seg.id, "name": seg.name, "description": seg.description})
    return matching


@router.get("/{contact_id}/bookings")
def contact_bookings(
    contact_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Historial de reservas desde la DB fuente de HotBoat."""
    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    engine = _hotboat_engine()
    try:
        with engine.connect() as conn:
            # Une reservas donde el contacto es el titular (aa.email) con
            # reservas donde solo firmó los T&C como pasajero (hotboat_signatures)
            # — mismo criterio de asistencia que sync_hotboat.py usa para
            # veces_hotboat, pero aquí en vivo para el listado del perfil.
            rows = conn.execute(text("""
                SELECT * FROM (
                    SELECT aa.fecha, aa.status, aa.ingreso_total, aa.como_supieron, aa.extras_json
                    FROM all_appointments aa
                    WHERE LOWER(aa.email) = LOWER(:email)
                    UNION
                    SELECT aa.fecha, aa.status, aa.ingreso_total, aa.como_supieron, aa.extras_json
                    FROM all_appointments aa
                    JOIN hotboat_signatures hs
                      ON hs.booking_ref = aa.appointment_id
                      OR hs.booking_ref = ('AA-' || aa.id::text)
                      OR hs.booking_ref = TRIM(aa.source_id)
                    WHERE LOWER(hs.passenger_email) = LOWER(:email)
                ) combined
                ORDER BY fecha DESC
                LIMIT 50
            """), {"email": contact.email}).fetchall()
        return [
            {
                "fecha": str(r.fecha),
                "status": r.status,
                "ingreso_total": float(r.ingreso_total) if r.ingreso_total else None,
                "como_supieron": r.como_supieron,
                "extras": r.extras_json if r.extras_json else {},
            }
            for r in rows
        ]
    except Exception as exc:
        # Source DB not available — return empty without crashing
        return []
    finally:
        engine.dispose()


@router.post("/{contact_id}/attach_booking")
def attach_booking(
    contact_id: int,
    payload: dict,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Asocia manualmente una reserva de HotBoat a este contacto, como si
    hubiera firmado los T&C en ese paseo (p. ej. cuando quedó registrado en
    el sistema pero se olvidó pedirle la firma en el momento)."""
    booking_ref = (payload or {}).get("booking_ref", "").strip()
    if not booking_ref:
        raise HTTPException(status_code=400, detail="Falta booking_ref")

    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    if not contact.email:
        raise HTTPException(status_code=400, detail="Este contacto no tiene email registrado")

    engine = _hotboat_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS hotboat_signatures (
                    id               SERIAL PRIMARY KEY,
                    booking_ref      VARCHAR(50)  NOT NULL,
                    passenger_name   VARCHAR(255) NOT NULL,
                    passenger_email  VARCHAR(255),
                    passenger_phone  VARCHAR(50),
                    passenger_birthday DATE,
                    accepted_tc      BOOLEAN      DEFAULT TRUE,
                    ip_address       VARCHAR(50),
                    created_at       TIMESTAMPTZ  DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                INSERT INTO hotboat_signatures
                    (booking_ref, passenger_name, passenger_email, passenger_phone, accepted_tc, ip_address)
                VALUES (:booking_ref, :passenger_name, :passenger_email, :passenger_phone, TRUE, 'admin-manual')
            """), {
                "booking_ref": booking_ref,
                "passenger_name": contact.name or contact.email,
                "passenger_email": contact.email,
                "passenger_phone": contact.phone,
            })
            conn.commit()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo escribir en la DB de HotBoat: {exc}")
    finally:
        engine.dispose()

    return {"ok": True}


@router.get("/{contact_id}/email_activity")
def contact_email_activity(
    contact_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Feed de eventos de email para el contacto (enviados, abiertos, clics)."""
    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    sends = session.exec(
        select(CampaignSend)
        .where(CampaignSend.contact_id == contact_id)
        .order_by(CampaignSend.sent_at.desc())
    ).all()
    if not sends:
        return []

    campaign_ids = list({s.campaign_id for s in sends})
    camps = {c.id: c for c in session.exec(select(Campaign).where(Campaign.id.in_(campaign_ids))).all()}

    events = []
    for s in sends:
        camp = camps.get(s.campaign_id)
        base = {
            "campaign_id": s.campaign_id,
            "campaign_name": camp.name if camp else f"Campaña #{s.campaign_id}",
        }
        if s.clicked_at:
            events.append({**base, "type": "clicked",   "timestamp": s.clicked_at.isoformat()})
        if s.opened_at:
            events.append({**base, "type": "opened",    "timestamp": s.opened_at.isoformat()})
        if s.delivered_at:
            events.append({**base, "type": "delivered", "timestamp": s.delivered_at.isoformat()})
        if s.bounced_at:
            events.append({**base, "type": "bounced",   "timestamp": s.bounced_at.isoformat()})
        if s.sent_at:
            events.append({**base, "type": "sent",      "timestamp": s.sent_at.isoformat()})

    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return events[:60]


@router.get("/{contact_id}/email_sends")
def contact_email_sends(
    contact_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Resumen por campaña: qué le enviamos, si abrió, si hizo clic."""
    contact = session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    sends = session.exec(
        select(CampaignSend)
        .where(CampaignSend.contact_id == contact_id)
        .order_by(CampaignSend.sent_at.desc())
    ).all()
    if not sends:
        return []

    campaign_ids = list({s.campaign_id for s in sends})
    camps = {c.id: c for c in session.exec(select(Campaign).where(Campaign.id.in_(campaign_ids))).all()}

    return [
        {
            "campaign_id":   s.campaign_id,
            "campaign_name": camps[s.campaign_id].name if s.campaign_id in camps else f"Campaña #{s.campaign_id}",
            "status":        s.status,
            "sent_at":       s.sent_at.isoformat()       if s.sent_at       else None,
            "delivered_at":  s.delivered_at.isoformat()  if s.delivered_at  else None,
            "opened_at":     s.opened_at.isoformat()     if s.opened_at     else None,
            "clicked_at":    s.clicked_at.isoformat()    if s.clicked_at    else None,
            "bounced_at":    s.bounced_at.isoformat()    if s.bounced_at    else None,
        }
        for s in sends
    ]


@router.post("/import/csv", status_code=201)
def import_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Importa contactos desde CSV. Columnas requeridas: email. Opcionales: name, phone, language, origin_utm."""
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    created = 0
    skipped = 0
    for row in reader:
        email = row.get("email", "").strip().lower()
        if not email:
            skipped += 1
            continue
        existing = session.exec(select(Contact).where(Contact.email == email)).first()
        if existing:
            skipped += 1
            continue
        contact = Contact(
            email=email,
            name=row.get("name", "").strip() or None,
            phone=row.get("phone", "").strip() or None,
            language=row.get("language", "").strip() or None,
            origin_utm=row.get("origin_utm", "").strip() or None,
            opted_in=True,
            opted_in_at=datetime.utcnow(),
        )
        session.add(contact)
        created += 1
    session.commit()
    return {"created": created, "skipped": skipped}
