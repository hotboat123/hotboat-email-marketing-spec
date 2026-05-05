from datetime import datetime
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select
from jinja2 import Template as JTemplate
import resend
from app.database import get_session, engine
from app.core.config import settings
from app.core.deps import get_current_user, require_editor
from app.models.user import User
from app.models.campaign import Campaign, CampaignCreate, CampaignRead, CampaignStats, CampaignUpdate, CampaignSend
from app.models.segment import Segment
from app.models.template import Template
from app.services.segment_evaluator import evaluate_segment
from app.services.email_sender import send_campaign_sync

router = APIRouter()


@router.get("/", response_model=List[CampaignRead])
def list_campaigns(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return session.exec(select(Campaign).order_by(Campaign.created_at.desc())).all()


@router.post("/", response_model=CampaignRead, status_code=201)
def create_campaign(
    payload: CampaignCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    campaign = Campaign(**payload.model_dump(), created_by=current_user.id)
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: int, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    c = session.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return c


@router.patch("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    c = session.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    if c.status == "sent":
        raise HTTPException(status_code=400, detail="No se puede editar una campaña ya enviada")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(
    campaign_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    c = session.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    if c.status in ("sending", "sent"):
        raise HTTPException(status_code=400, detail="No se puede eliminar campaña enviada o en envío")
    session.delete(c)
    session.commit()


@router.post("/{campaign_id}/send", response_model=CampaignRead)
def send_campaign_now(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    c = session.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    if c.status not in ("draft", "scheduled"):
        raise HTTPException(status_code=400, detail=f"Estado inválido para envío: {c.status}")

    seg = session.get(Segment, c.segment_id)
    if not seg:
        raise HTTPException(status_code=400, detail="Segmento no encontrado")

    contacts = evaluate_segment(seg.conditions, session)
    if not contacts:
        raise HTTPException(status_code=400, detail="El segmento no tiene contactos con opt-in")

    c.status = "sending"
    session.add(c)
    session.commit()
    session.refresh(c)

    contact_ids = [c.id for c in contacts]
    background_tasks.add_task(send_campaign_sync, campaign_id, contact_ids)
    return c


@router.post("/{campaign_id}/send-test")
def send_test_email(
    campaign_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Envía un email de prueba al usuario autenticado."""
    c = session.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    tpl = session.get(Template, c.template_id)
    if not tpl:
        raise HTTPException(status_code=400, detail="Plantilla no encontrada")

    nombre = current_user.name or current_user.email.split("@")[0]
    html = JTemplate(tpl.html_content).render(nombre=nombre)

    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [current_user.email],
            "subject": f"[PRUEBA] {c.subject}",
            "html": html,
        })
        return {"ok": True, "sent_to": current_user.email}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{campaign_id}/stats", response_model=CampaignStats)
def campaign_stats(campaign_id: int, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    c = session.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")

    sends = session.exec(select(CampaignSend).where(CampaignSend.campaign_id == campaign_id)).all()
    total = len(sends)
    sent = sum(1 for s in sends if s.status not in ("queued",))
    delivered = sum(1 for s in sends if s.status == "delivered")
    opened = sum(1 for s in sends if s.opened_at is not None)
    clicked = sum(1 for s in sends if s.clicked_at is not None)
    bounced = sum(1 for s in sends if s.status == "bounced")
    complained = sum(1 for s in sends if s.status == "complained")

    base = delivered or sent or 1
    return CampaignStats(
        campaign_id=campaign_id,
        total=total,
        sent=sent,
        delivered=delivered,
        opened=opened,
        clicked=clicked,
        bounced=bounced,
        complained=complained,
        open_rate=round(opened / base * 100, 1),
        click_rate=round(clicked / base * 100, 1),
        bounce_rate=round(bounced / (sent or 1) * 100, 1),
    )
