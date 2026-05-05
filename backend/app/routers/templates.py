from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.core.deps import get_current_user, require_editor
from app.models.user import User
from app.models.template import Template, TemplateCreate, TemplateRead, TemplateUpdate

router = APIRouter()


@router.get("/", response_model=List[TemplateRead])
def list_templates(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return session.exec(select(Template)).all()


@router.post("/", response_model=TemplateRead, status_code=201)
def create_template(
    payload: TemplateCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    tpl = Template(**payload.model_dump(), created_by=current_user.id)
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(template_id: int, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return tpl


@router.patch("/{template_id}", response_model=TemplateRead)
def update_template(
    template_id: int,
    payload: TemplateUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(tpl, k, v)
    tpl.updated_at = datetime.utcnow()
    session.add(tpl)
    session.commit()
    session.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    session.delete(tpl)
    session.commit()


@router.post("/{template_id}/duplicate", response_model=TemplateRead, status_code=201)
def duplicate_template(
    template_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    tpl = session.get(Template, template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    copy = Template(
        name=f"{tpl.name} (copia)",
        subject_default=tpl.subject_default,
        preview_text=tpl.preview_text,
        html_content=tpl.html_content,
        json_blocks=tpl.json_blocks,
        created_by=current_user.id,
    )
    session.add(copy)
    session.commit()
    session.refresh(copy)
    return copy
