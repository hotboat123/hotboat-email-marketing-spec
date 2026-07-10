import csv
import io
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from app.database import get_session
from app.core.deps import get_current_user, require_editor
from app.models.user import User
from app.models.contact_crm import ContactCRM, ContactCRMRead, CallStatusUpdate
from app.models.call_activity import CallActivity, CallActivityRead

router = APIRouter()

VALID_CALL_STATUSES = {"pending", "called", "no_answer", "booked", "not_interested"}


@router.get("/contacts", response_model=List[ContactCRMRead])
def list_crm_contacts(
    call_status: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    ad_source: Optional[str] = None,
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
    query = query.order_by(ContactCRM.reservation_score.desc().nullslast()).offset(skip).limit(limit)
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
        "ad_source", "veces_hotboat", "ultima_visita",
    ])
    for c in contacts:
        writer.writerow([
            c.phone, c.name, c.email, c.reservation_score, c.call_status,
            c.ad_source, c.veces_hotboat, c.ultima_visita,
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=crm_contacts.csv"},
    )


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
