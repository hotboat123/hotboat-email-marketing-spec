import csv
import io
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlmodel import Session, select

from app.database import get_session
from app.core.deps import get_current_user, require_editor
from app.models.user import User
from app.models.contact_crm import ContactCRM, ContactCRMRead, CallStatusUpdate
from app.models.call_activity import CallActivity, CallActivityRead
from app.services.sync_hotboat import _source_engine

router = APIRouter()

VALID_CALL_STATUSES = {"pending", "called", "no_answer", "booked", "not_interested"}


SORT_COLUMNS = {
    "score": ContactCRM.reservation_score,
    "last_interaction": ContactCRM.last_interaction_at,  # ultimo mensaje de WhatsApp
    "booking": ContactCRM.ultima_visita,  # ultima reserva confirmada
}


@router.get("/contacts", response_model=List[ContactCRMRead])
def list_crm_contacts(
    call_status: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    ad_source: Optional[str] = None,
    sort: str = Query("score", pattern="^(score|last_interaction|booking)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    query = select(ContactCRM)
    if call_status:
        query = query.where(ContactCRM.call_status == call_status)
    if min_score is not None:
        query = query.where(ContactCRM.reservation_score >= min_score)
    if ad_source:
        query = query.where(ContactCRM.ad_source.ilike(f"%{ad_source}%"))
    query = query.order_by(SORT_COLUMNS[sort].desc().nullslast()).offset(skip).limit(limit)
    return session.exec(query).all()


@router.get("/contacts/export/csv")
def export_crm_contacts_csv(
    call_status: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    query = select(ContactCRM)
    if call_status:
        query = query.where(ContactCRM.call_status == call_status)
    if min_score is not None:
        query = query.where(ContactCRM.reservation_score >= min_score)
    query = query.order_by(ContactCRM.reservation_score.desc().nullslast())
    contacts = session.exec(query).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "phone", "name", "email", "reservation_score", "call_status",
        "ad_source", "veces_hotboat", "last_interaction_at", "ultima_visita",
    ])
    for c in contacts:
        writer.writerow([
            c.phone, c.name, c.email, c.reservation_score, c.call_status,
            c.ad_source, c.veces_hotboat, c.last_interaction_at, c.ultima_visita,
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=crm_contacts.csv"},
    )


@router.get("/contacts/by_contact/{contact_id}", response_model=ContactCRMRead)
def get_crm_by_contact(
    contact_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Busca el registro CRM (WhatsApp/telefono) vinculado a un contacto de email,
    para poder mostrar ambas vistas fusionadas en /contacts/{id}."""
    contact = session.exec(select(ContactCRM).where(ContactCRM.linked_contact_id == contact_id)).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Sin registro CRM vinculado")
    return contact


@router.get("/contacts/{contact_crm_id}", response_model=ContactCRMRead)
def get_crm_contact(
    contact_crm_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return contact


@router.get("/contacts/{contact_crm_id}/call_activity", response_model=List[CallActivityRead])
def get_call_activity(
    contact_crm_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return session.exec(
        select(CallActivity)
        .where(CallActivity.contact_crm_id == contact_crm_id)
        .order_by(CallActivity.created_at.desc())
    ).all()


@router.get("/contacts/{contact_crm_id}/conversations")
def get_crm_conversations(
    contact_crm_id: int,
    limit: int = Query(100, le=500),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Historial de mensajes de WhatsApp para este contacto (lectura directa de
    hotboat-whatsapp). Compara con y sin '+' porque los mensajes anteriores al
    backfill de normalizacion de telefono quedaron guardados sin el '+'."""
    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    if not contact.phone:
        return []

    phone_digits = contact.phone.lstrip("+")
    engine = _source_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT message_text, response_text, message_type, direction, created_at
            FROM whatsapp_conversations
            WHERE phone_number IN (:phone, :phone_digits)
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"phone": contact.phone, "phone_digits": phone_digits, "limit": limit}).fetchall()

    return [
        {
            "message_text": r.message_text,
            "response_text": r.response_text,
            "message_type": r.message_type,
            "direction": r.direction,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/contacts/{contact_crm_id}/web_activity")
def get_crm_web_activity(
    contact_crm_id: int,
    limit: int = Query(200, le=1000),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Eventos de navegacion web para este contacto. Combina las dos formas de
    identidad que hoy existen en hotboat-whatsapp:
    - link_token (tracked_quote_links): cubre a quien el bot le mando un link.
    - booking_visitor_identity (session_id/visitor_id): cubre a quien llego
      directo a la web (hotboat.cl, ads, organico) y quedo identificado al
      reservar — sin haber pasado nunca por un link de WhatsApp."""
    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    if not contact.phone:
        return []

    phone_digits = contact.phone.lstrip("+")
    engine = _source_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT DISTINCT bve.event_type, bve.extra_date, bve.time_label,
                       bve.recorded_at, bve.session_id
                FROM booking_visitor_events bve
                WHERE bve.link_token IN (
                    SELECT token FROM tracked_quote_links WHERE phone IN (:phone, :phone_digits)
                ) OR bve.session_id IN (
                    SELECT session_id FROM booking_visitor_identity WHERE phone IN (:phone, :phone_digits)
                ) OR bve.visitor_id IN (
                    SELECT visitor_id FROM booking_visitor_identity
                    WHERE phone IN (:phone, :phone_digits) AND visitor_id IS NOT NULL
                )
                ORDER BY bve.recorded_at DESC
                LIMIT :limit
            """), {"phone": contact.phone, "phone_digits": phone_digits, "limit": limit}).fetchall()
    except Exception:
        # Tabla/columnas pueden no existir aun en algunos entornos — no romper
        # el detalle del contacto.
        return []

    return [
        {
            "event_type": r.event_type,
            "extra_date": r.extra_date,
            "time_label": r.time_label,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            "session_id": r.session_id,
        }
        for r in rows
    ]


@router.patch("/contacts/{contact_crm_id}/call_status", response_model=ContactCRMRead)
def update_call_status(
    contact_crm_id: int,
    payload: CallStatusUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(require_editor),
):
    if payload.call_status not in VALID_CALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"call_status inválido. Válidos: {sorted(VALID_CALL_STATUSES)}")

    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    old_status = contact.call_status
    now = datetime.utcnow()
    contact.call_status = payload.call_status
    contact.call_status_updated_at = now
    contact.updated_at = now
    session.add(contact)
    session.add(CallActivity(
        contact_crm_id=contact_crm_id,
        old_status=old_status,
        new_status=payload.call_status,
        note=payload.note,
        created_by=payload.created_by or getattr(user, "email", None),
        created_at=now,
    ))
    session.commit()
    session.refresh(contact)
    return contact
