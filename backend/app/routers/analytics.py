from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from app.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.models.contact import Contact
from app.models.campaign import Campaign, CampaignSend
from app.models.segment import Segment
from app.models.template import Template

router = APIRouter()


@router.get("/overview")
def overview(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    total_contacts = session.exec(select(func.count(Contact.id))).one()
    opted_in = session.exec(select(func.count(Contact.id)).where(Contact.opted_in == True)).one()  # noqa
    total_campaigns = session.exec(select(func.count(Campaign.id))).one()
    sent_campaigns = session.exec(select(func.count(Campaign.id)).where(Campaign.status == "sent")).one()
    total_sends = session.exec(select(func.count(CampaignSend.id))).one()
    delivered = session.exec(select(func.count(CampaignSend.id)).where(CampaignSend.status == "delivered")).one()
    opened = session.exec(select(func.count(CampaignSend.id)).where(CampaignSend.opened_at.isnot(None))).one()
    total_segments = session.exec(select(func.count(Segment.id))).one()
    total_templates = session.exec(select(func.count(Template.id))).one()

    return {
        "contacts": {"total": total_contacts, "opted_in": opted_in},
        "campaigns": {"total": total_campaigns, "sent": sent_campaigns},
        "sends": {
            "total": total_sends,
            "delivered": delivered,
            "opened": opened,
            "open_rate": round(opened / delivered * 100, 1) if delivered else 0,
        },
        "segments": total_segments,
        "templates": total_templates,
    }


@router.get("/campaigns/recent")
def recent_campaigns(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    campaigns = session.exec(
        select(Campaign).where(Campaign.status == "sent").order_by(Campaign.sent_at.desc()).limit(5)
    ).all()
    result = []
    for c in campaigns:
        sends = session.exec(select(CampaignSend).where(CampaignSend.campaign_id == c.id)).all()
        total = len(sends)
        opened = sum(1 for s in sends if s.opened_at)
        result.append({
            "id": c.id,
            "name": c.name,
            "subject": c.subject,
            "sent_at": c.sent_at,
            "total": total,
            "open_rate": round(opened / total * 100, 1) if total else 0,
        })
    return result
