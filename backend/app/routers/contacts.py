import csv
import io
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlmodel import Session, select
from app.database import get_session
from app.core.deps import get_current_user, require_editor
from app.models.user import User
from app.models.contact import Contact, ContactCreate, ContactRead, ContactUpdate

router = APIRouter()


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
    session.delete(contact)
    session.commit()


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
