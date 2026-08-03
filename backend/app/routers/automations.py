import uuid
from datetime import datetime, date, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from jinja2 import Template as JTemplate
from sqlalchemy import create_engine, text
from sqlmodel import Session, select, func
from app.core.config import settings
from app.database import get_session
from app.core.deps import get_current_user, require_editor
from app.email.send_email import default_from_address, send_email
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
    VALID = {"abandoned_booking", "abandoned_followup", "welcome", "post_visit", "reactivation", "birthday"}
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

    html = _inject_footer(JTemplate(tpl.html_content).render(**sample_vars), settings.NOTIFY_EMAIL)
    result = send_email(
        to=settings.NOTIFY_EMAIL,
        subject=f"[TEST] {a.subject}",
        html=html,
        from_address=default_from_address(),
        headers=_unsub_headers(settings.NOTIFY_EMAIL),
        trigger="automation_test_send",
    )
    if not result["sent"]:
        raise HTTPException(status_code=500, detail=f"Error al enviar: {result['reason']}")

    # Test sends still cost real money on whichever provider is active — track
    # them the same way a real run would (contact_id=None since there's no
    # real contact behind a test) so they show up in Correos enviados and
    # count toward the SES/Resend totals used for billing.
    session.add(AutomationRun(
        automation_id=a.id,
        contact_email=settings.NOTIFY_EMAIL,
        trigger_key=f"test_{uuid.uuid4().hex[:12]}",
        status="sent",
        resend_id=result.get("message_id"),
        executed_at=datetime.utcnow(),
    ))
    session.commit()

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

    # Opened/clicked come from the Resend webhook (app/routers/webhooks.py),
    # matched by resend_id — same shape as campaign_stats() in campaigns.py.
    delivered = sum(1 for r in runs if r.delivered_at is not None or r.status == "sent")
    opened = sum(1 for r in runs if r.opened_at is not None)
    clicked = sum(1 for r in runs if r.clicked_at is not None)
    bounced = sum(1 for r in runs if r.bounced_at is not None)
    base = delivered or sent or 1
    return {
        "total": total, "sent": sent, "failed": failed, "last_run": last_run,
        "delivered": delivered, "opened": opened, "clicked": clicked, "bounced": bounced,
        "open_rate": round(opened / base * 100, 1),
        "click_rate": round(clicked / base * 100, 1),
    }


@router.get("/{auto_id}/conversions")
def automation_conversions(
    auto_id: int,
    days: int = Query(default=60, ge=1, le=365),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Atribución de reservas: contactos que recibieron un envío de esta
    automatización y tuvieron una visita confirmada en HotBoat dentro de
    `days` días posteriores a SU envío. A diferencia de campaign_conversions
    (una campaña = un solo sent_at para todos los contactos), cada
    AutomationRun dispara en un momento distinto por contacto (cumpleaños,
    reserva abandonada, etc.) — así que la ventana se evalúa por envío, no
    de forma global. Si un mismo email tuvo varios envíos de esta
    automatización, una reserva que cae en más de una ventana se cuenta una
    sola vez (mismo criterio de no-doble-conteo que sync_hotboat.py).
    """
    automation = session.get(Automation, auto_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")

    empty = {"automation_id": auto_id, "window_days": days, "bookings": 0, "revenue": 0.0, "converted_contacts": 0}

    runs = session.exec(
        select(AutomationRun).where(
            AutomationRun.automation_id == auto_id,
            AutomationRun.status == "sent",
        )
    ).all()

    windows_by_email: dict[str, list[tuple[date, date]]] = {}
    for r in runs:
        if not r.contact_email:
            continue
        start = r.triggered_at.date()
        windows_by_email.setdefault(r.contact_email, []).append((start, start + timedelta(days=days)))
    if not windows_by_email:
        return empty

    emails = list(windows_by_email.keys())
    min_start = min(w[0] for windows in windows_by_email.values() for w in windows)
    max_end = max(w[1] for windows in windows_by_email.values() for w in windows)

    src_url = settings.HOTBOAT_DATABASE_URL or settings.DATABASE_URL
    try:
        src_engine = create_engine(src_url)
        with src_engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT email, fecha, ingreso_total
                FROM all_appointments
                WHERE email = ANY(:emails)
                  AND fecha >= :start_date
                  AND fecha <= :end_date
                  AND status NOT IN ('cancelled', 'no_show', 'pending')
            """), {
                "emails": emails,
                "start_date": min_start,
                "end_date": max_end,
            }).fetchall()
    except Exception:
        return empty

    total_bookings = 0
    total_revenue = 0.0
    converted_emails: set[str] = set()
    for row in rows:
        if any(start <= row.fecha <= end for start, end in windows_by_email.get(row.email, [])):
            total_bookings += 1
            total_revenue += float(row.ingreso_total or 0)
            converted_emails.add(row.email)

    return {
        "automation_id": auto_id,
        "window_days": days,
        "bookings": total_bookings,
        "revenue": total_revenue,
        "converted_contacts": len(converted_emails),
    }
