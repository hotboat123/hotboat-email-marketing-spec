"""
Automation engine — runs every 15 minutes in a background thread.
Implements 4 trigger types: abandoned_booking, welcome, post_visit, reactivation.
"""
import logging
import threading
import time
from datetime import datetime, timedelta

import resend
from jinja2 import Template as JTemplate
from sqlalchemy import create_engine, text
from sqlmodel import Session, select

from app.core.config import settings
from app.database import engine as db_engine
from app.models.automation import Automation, AutomationRun
from app.models.contact import Contact
from app.models.template import Template
from app.services.email_sender import _inject_footer, _unsub_headers

logger = logging.getLogger(__name__)


def _source_engine():
    url = settings.HOTBOAT_DATABASE_URL or settings.DATABASE_URL
    return create_engine(url)


def _already_sent(session: Session, automation_id: int, trigger_key: str) -> bool:
    return session.exec(
        select(AutomationRun).where(
            AutomationRun.automation_id == automation_id,
            AutomationRun.trigger_key == trigger_key,
        )
    ).first() is not None


def _send_email(
    session: Session,
    automation: Automation,
    contact: Contact,
    trigger_key: str,
) -> None:
    tpl = session.get(Template, automation.template_id)
    if not tpl:
        logger.warning("Automation %d: template %d not found", automation.id, automation.template_id)
        return

    vars_ = {
        "nombre": contact.name or contact.email.split("@")[0],
        "email": contact.email,
        "veces_hotboat": contact.veces_hotboat,
        "ultima_visita": str(contact.ultima_visita) if contact.ultima_visita else "",
        "ticket_medio": contact.ticket_medio or 0,
    }
    html = _inject_footer(JTemplate(tpl.html_content).render(**vars_), contact.email)
    resend.api_key = settings.RESEND_API_KEY

    run = AutomationRun(
        automation_id=automation.id,
        contact_id=contact.id,
        contact_email=contact.email,
        trigger_key=trigger_key,
        triggered_at=datetime.utcnow(),
    )
    try:
        result = resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [contact.email],
            "subject": automation.subject,
            "html": html,
            "headers": _unsub_headers(contact.email),
        })
        resend_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        run.status = "sent"
        run.resend_id = resend_id
        run.executed_at = datetime.utcnow()
        logger.info("Automation %d sent to %s (key=%s)", automation.id, contact.email, trigger_key)
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)[:500]
        run.executed_at = datetime.utcnow()
        logger.error("Automation %d failed for %s: %s", automation.id, contact.email, exc)

    session.add(run)
    session.commit()


# ── Trigger handlers ──────────────────────────────────────────────────────────

def _check_abandoned_booking(auto: Automation, session: Session) -> None:
    """Poll source DB for pending bookings older than delay_hours (within last 7 days)."""
    config = auto.trigger_config or {}
    delay_hours = int(config.get("delay_hours", 2))
    cutoff_old = datetime.utcnow() - timedelta(hours=delay_hours)
    cutoff_recent = datetime.utcnow() - timedelta(days=7)

    try:
        src = _source_engine()
        with src.connect() as conn:
            rows = conn.execute(text("""
                SELECT email, nombre_cliente, fecha
                FROM all_appointments
                WHERE status = 'pending'
                  AND fecha <= :cutoff_old
                  AND fecha >= :cutoff_recent
                  AND email IS NOT NULL AND email <> ''
                ORDER BY fecha DESC
                LIMIT 200
            """), {"cutoff_old": cutoff_old, "cutoff_recent": cutoff_recent}).fetchall()
    except Exception as exc:
        logger.error("Automation %d: cannot read source DB: %s", auto.id, exc)
        return

    for row in rows:
        email = row.email.lower().strip()
        # Use email + date as the dedup key (one reminder per booking date per contact)
        fecha_str = str(row.fecha.date()) if hasattr(row.fecha, "date") else str(row.fecha)[:10]
        trigger_key = f"abandoned:{email}:{fecha_str}"
        if _already_sent(session, auto.id, trigger_key):
            continue
        contact = session.exec(select(Contact).where(Contact.email == email)).first()
        if not contact or not contact.opted_in:
            continue
        _send_email(session, auto, contact, trigger_key)


def _check_welcome(auto: Automation, session: Session) -> None:
    """Fire welcome email to contacts created in the last polling window."""
    config = auto.trigger_config or {}
    delay_hours = int(config.get("delay_hours", 0))
    # Look at contacts created in the window that matches the delay
    window_end = datetime.utcnow() - timedelta(hours=delay_hours)
    window_start = window_end - timedelta(minutes=20)

    contacts = session.exec(
        select(Contact).where(
            Contact.created_at >= window_start,
            Contact.created_at <= window_end,
            Contact.opted_in == True,
        )
    ).all()

    for contact in contacts:
        trigger_key = f"welcome:{contact.id}"
        if _already_sent(session, auto.id, trigger_key):
            continue
        _send_email(session, auto, contact, trigger_key)


def _check_post_visit(auto: Automation, session: Session) -> None:
    """Fire N days after ultima_visita."""
    config = auto.trigger_config or {}
    delay_days = int(config.get("delay_days", 3))
    target_date = (datetime.utcnow() - timedelta(days=delay_days)).date()

    contacts = session.exec(
        select(Contact).where(
            Contact.ultima_visita == target_date,
            Contact.opted_in == True,
        )
    ).all()

    for contact in contacts:
        trigger_key = f"postvisit:{contact.id}:{target_date}"
        if _already_sent(session, auto.id, trigger_key):
            continue
        _send_email(session, auto, contact, trigger_key)


def _check_reactivation(auto: Automation, session: Session) -> None:
    """Fire when contact hasn't visited in N days, respecting a cooldown period."""
    config = auto.trigger_config or {}
    inactivity_days = int(config.get("inactivity_days", 90))
    cooldown_days = int(config.get("cooldown_days", 180))

    cutoff_date = (datetime.utcnow() - timedelta(days=inactivity_days)).date()
    cooldown_start = datetime.utcnow() - timedelta(days=cooldown_days)

    contacts = session.exec(
        select(Contact).where(
            Contact.ultima_visita != None,
            Contact.ultima_visita <= cutoff_date,
            Contact.opted_in == True,
        )
    ).all()

    for contact in contacts:
        recent_run = session.exec(
            select(AutomationRun).where(
                AutomationRun.automation_id == auto.id,
                AutomationRun.contact_id == contact.id,
                AutomationRun.triggered_at >= cooldown_start,
                AutomationRun.status == "sent",
            )
        ).first()
        if recent_run:
            continue
        # Weekly dedup to avoid burst on startup
        week = datetime.utcnow().strftime("%Y-W%W")
        trigger_key = f"reactivation:{contact.id}:{week}"
        if _already_sent(session, auto.id, trigger_key):
            continue
        _send_email(session, auto, contact, trigger_key)


HANDLERS = {
    "abandoned_booking": _check_abandoned_booking,
    "welcome": _check_welcome,
    "post_visit": _check_post_visit,
    "reactivation": _check_reactivation,
}


def run_automations() -> None:
    with Session(db_engine) as session:
        automations = session.exec(
            select(Automation).where(Automation.status == "active")
        ).all()
        for auto in automations:
            handler = HANDLERS.get(auto.trigger_type)
            if handler:
                try:
                    handler(auto, session)
                except Exception as exc:
                    logger.exception("Automation %d (%s) error: %s", auto.id, auto.trigger_type, exc)


def start_scheduler() -> None:
    def loop():
        # Small delay to let the app fully start
        time.sleep(10)
        while True:
            try:
                run_automations()
            except Exception as exc:
                logger.exception("Automation scheduler error: %s", exc)
            time.sleep(60)  # 1 minute

    t = threading.Thread(target=loop, daemon=True, name="automation-scheduler")
    t.start()
    logger.info("Automation scheduler started (interval: 1 min)")
