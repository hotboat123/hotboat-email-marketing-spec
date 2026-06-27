from datetime import datetime, date
from typing import List
import resend
from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Template as JTemplate
from sqlmodel import Session, select, func
from app.core.config import settings
from app.database import get_session
from app.core.deps import get_current_user, require_editor
from app.models.user import User
from app.models.template import Template
from app.models.automation import (
    Automation, AutomationCreate, AutomationRead, AutomationUpdate,
    AutomationRun, AutomationRunRead,
)
from app.services.email_sender import _inject_footer, _unsub_headers

router = APIRouter()


@router.get("", response_model=List[AutomationRead])
def list_automations(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return session.exec(select(Automation).order_by(Automation.created_at.desc())).all()


@router.post("", response_model=AutomationRead, status_code=201)
def create_automation(
    payload: AutomationCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    VALID = {"abandoned_booking", "welcome", "post_visit", "reactivation"}
    if payload.trigger_type not in VALID:
        raise HTTPException(status_code=400, detail=f"trigger_type debe ser uno de: {', '.join(VALID)}")
    auto = Automation(**payload.model_dump(), created_by=current_user.id)
    session.add(auto)
    session.commit()
    session.refresh(auto)
    return auto


@router.get("/{auto_id}", response_model=AutomationRead)
def get_automation(auto_id: int, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    a = session.get(Automation, auto_id)
    if not a:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    return a


@router.patch("/{auto_id}", response_model=AutomationRead)
def update_automation(
    auto_id: int,
    payload: AutomationUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    a = session.get(Automation, auto_id)
    if not a:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    a.updated_at = datetime.utcnow()
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


@router.delete("/{auto_id}", status_code=204)
def delete_automation(
    auto_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    a = session.get(Automation, auto_id)
    if not a:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    session.delete(a)
    session.commit()


@router.post("/{auto_id}/toggle", response_model=AutomationRead)
def toggle_automation(
    auto_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    a = session.get(Automation, auto_id)
    if not a:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    a.status = "paused" if a.status == "active" else "active"
    a.updated_at = datetime.utcnow()
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


@router.get("/{auto_id}/runs", response_model=List[AutomationRunRead])
def list_runs(
    auto_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    return session.exec(
        select(AutomationRun)
        .where(AutomationRun.automation_id == auto_id)
        .order_by(AutomationRun.triggered_at.desc())
        .limit(100)
    ).all()


@router.post("/{auto_id}/test")
def test_automation(
    auto_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Envía el template de la automatización con datos de prueba al NOTIFY_EMAIL."""
    if not settings.NOTIFY_EMAIL:
        raise HTTPException(status_code=400, detail="NOTIFY_EMAIL no está configurado en el servidor")

    a = session.get(Automation, auto_id)
    if not a:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")

    tpl = session.get(Template, a.template_id)
    if not tpl:
        raise HTTPException(status_code=400, detail="Esta automatización no tiene plantilla asignada")

    today = date.today().strftime("%d/%m/%Y")
    sample_vars = {
        "nombre": "Test HotBoat",
        "email": settings.NOTIFY_EMAIL,
        "veces_hotboat": 3,
        "ultima_visita": today,
        "ticket_medio": 50000,
        "servicio": "Tour en Kayak — Lago Villarrica",
        "fecha_reserva": today,
        "hora_reserva": "10:00",
        "personas": "2 adultos + 1 niño",
        "num_adultos": 2,
        "num_ninos": 1,
        "ingreso_total": "$50.000",
        "pay_url": f"{settings.WOO_URL}/es/checkout/order-pay/0/?pay_for_order=true&key=test_preview",
    }

    try:
        html = _inject_footer(JTemplate(tpl.html_content).render(**sample_vars), settings.NOTIFY_EMAIL)
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [settings.NOTIFY_EMAIL],
            "subject": f"[TEST] {a.subject}",
            "html": html,
            "headers": _unsub_headers(settings.NOTIFY_EMAIL),
        })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error al enviar: {exc}")

    return {"ok": True, "sent_to": settings.NOTIFY_EMAIL}


@router.get("/{auto_id}/stats")
def automation_stats(
    auto_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    runs = session.exec(
        select(AutomationRun).where(AutomationRun.automation_id == auto_id)
    ).all()
    total = len(runs)
    sent = sum(1 for r in runs if r.status == "sent")
    failed = sum(1 for r in runs if r.status == "failed")
    last_run = max((r.triggered_at for r in runs), default=None)
    return {"total": total, "sent": sent, "failed": failed, "last_run": last_run}
