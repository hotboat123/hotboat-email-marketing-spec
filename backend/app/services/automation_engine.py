"""
Automation engine — runs every 15 minutes in a background thread.
Implements 5 trigger types: abandoned_booking, welcome, post_visit, reactivation,
tc_signature.
"""
import logging
import re
import threading
import time
from datetime import datetime, timedelta

import httpx
import resend
from jinja2 import Template as JTemplate
from sqlalchemy import create_engine, text
from sqlmodel import Session, select

from app.core.config import settings
from app.database import engine as db_engine
from app.models.automation import Automation, AutomationRun
from app.models.campaign import Campaign, CampaignSend
from app.models.contact import Contact
from app.models.segment import Segment
from app.models.template import Template
from app.services.email_sender import _inject_footer, _unsub_headers, send_campaign_sync, _fmt_nombre
from app.services.segment_evaluator import evaluate_segment

logger = logging.getLogger(__name__)

# IDs de campañas que ya recibieron el recordatorio de 24h (se resetea al reiniciar el proceso)
_reminder_sent: set = set()


_WOO_FALLBACK = "https://hotboat.cl"
_WOO_STATUSES = {"pending", "on-hold", "failed"}


def _build_pay_link(woo_url: str, order_id, order_key: str) -> str:
    return f"{woo_url}/es/checkout/order-pay/{order_id}/?pay_for_order=true&key={order_key}"


def _get_woo_payment_link(source_id: str | None, email: str | None = None) -> str:
    """
    Obtiene la URL directa de pago de WooCommerce usando dos estrategias:
      1. Si source_id es numérico, busca la orden por ID en la REST API.
      2. Si falla o source_id no es numérico, busca las órdenes pendientes del email.
    Devuelve el fallback si ninguna estrategia funciona o las credenciales no están configuradas.
    """
    if not settings.WOO_CK or not settings.WOO_CS:
        return _WOO_FALLBACK

    woo_url = settings.WOO_URL.rstrip("/")
    auth = (settings.WOO_CK, settings.WOO_CS)

    # Estrategia 1: buscar por source_id si parece un order ID numérico
    if source_id and str(source_id).strip().isdigit():
        try:
            r = httpx.get(
                f"{woo_url}/wp-json/wc/v3/orders/{source_id}",
                auth=auth, timeout=8,
            )
            if r.status_code == 200:
                data = r.json()
                key = data.get("order_key", "")
                if data.get("status") in _WOO_STATUSES and key:
                    return _build_pay_link(woo_url, source_id, key)
        except Exception as exc:
            logger.warning("WooCommerce lookup by source_id %s failed: %s", source_id, exc)

    # Estrategia 2: buscar por email del cliente
    if email:
        try:
            r = httpx.get(
                f"{woo_url}/wp-json/wc/v3/orders",
                params={"email": email, "status": "pending,on-hold,failed", "per_page": 3, "orderby": "date", "order": "desc"},
                auth=auth, timeout=8,
            )
            if r.status_code == 200:
                orders = r.json()
                if orders:
                    o = orders[0]
                    order_id = o.get("id")
                    key = o.get("order_key", "")
                    if order_id and key:
                        return _build_pay_link(woo_url, order_id, key)
        except Exception as exc:
            logger.warning("WooCommerce lookup by email %s failed: %s", email, exc)

    return _WOO_FALLBACK


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
    extra_vars: dict | None = None,
) -> None:
    tpl = session.get(Template, automation.template_id)
    if not tpl:
        logger.warning("Automation %d: template %d not found", automation.id, automation.template_id)
        return

    vars_ = {
        "nombre": _fmt_nombre(contact.name, contact.email),
        "email": contact.email,
        "veces_hotboat": contact.veces_hotboat,
        "ultima_visita": str(contact.ultima_visita) if contact.ultima_visita else "",
        "ticket_medio": contact.ticket_medio or 0,
        **(extra_vars or {}),
    }
    html = _inject_footer(JTemplate(tpl.html_content).render(**vars_), contact.email)
    subject = JTemplate(automation.subject).render(**vars_)
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
            "subject": subject,
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
    """
    Fire when a booking has status='pending_payment' and paid_at IS NULL,
    created between delay_minutes and lookback_hours ago.
    Passes full booking details to the template as variables.
    """
    config = auto.trigger_config or {}
    delay_minutes = int(config.get("delay_minutes", 5))
    lookback_hours = int(config.get("lookback_hours", 24))

    now = datetime.utcnow()
    cutoff_old = now - timedelta(minutes=delay_minutes)
    cutoff_recent = now - timedelta(hours=lookback_hours)

    try:
        src = _source_engine()
        with src.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, email, nombre_cliente, servicio, fecha, hora,
                       num_adultos, num_ninos, ingreso_total, ingreso_reserva,
                       extras_json, created_at, payment_order_id
                FROM all_appointments
                WHERE status = 'pending_payment'
                  AND (paid_at IS NULL OR payment_status != 'completed')
                  AND created_at <= :cutoff_old
                  AND created_at >= :cutoff_recent
                  AND email IS NOT NULL AND email <> ''
                ORDER BY created_at DESC
                LIMIT 200
            """), {"cutoff_old": cutoff_old, "cutoff_recent": cutoff_recent}).fetchall()
    except Exception as exc:
        logger.error("Automation %d: cannot read source DB: %s", auto.id, exc)
        return

    for row in rows:
        email = row.email.lower().strip()
        # Dedup per booking row ID — one email per abandoned cart attempt
        trigger_key = f"abandoned:{row.id}"
        if _already_sent(session, auto.id, trigger_key):
            continue
        contact = session.exec(select(Contact).where(Contact.email == email)).first()
        if not contact or not contact.opted_in:
            continue

        # Personas: extraer del nombre del servicio "(Xp)" o usar adultos/niños
        m_personas = re.search(r'\((\d+)p\)', row.servicio or '')
        if m_personas:
            num_personas = int(m_personas.group(1))
            personas_str = f"{num_personas} persona{'s' if num_personas != 1 else ''}"
        else:
            adultos = int(row.num_adultos or 0)
            ninos = int(row.num_ninos or 0)
            personas_str = f"{adultos} adulto{'s' if adultos != 1 else ''}"
            if ninos:
                personas_str += f" + {ninos} niño{'s' if ninos != 1 else ''}"

        fecha_str = str(row.fecha) if row.fecha else ""
        hora_str = str(row.hora)[:5] if row.hora else ""

        # Montos
        def _fmt_clp(v) -> str:
            return f"${int(v):,}".replace(",", ".") if v else ""

        total_fmt = _fmt_clp(row.ingreso_total)
        reserva_fmt = _fmt_clp(row.ingreso_reserva or row.ingreso_total)

        # Extras: soporta dos formatos de extras_json
        extras_items: list[tuple[str, str]] = []
        ej = row.extras_json or {}
        if isinstance(ej, dict):
            if "extras" in ej and isinstance(ej["extras"], list):
                for e in ej["extras"]:
                    name = (e.get("name") or "").strip()
                    if not name:
                        continue
                    qty = int(e.get("quantity", 1))
                    price = int(e.get("price", 0)) * qty
                    label = f"{name}" + (f" x{qty}" if qty > 1 else "")
                    extras_items.append((label, _fmt_clp(price)))
            else:
                _SKIP = {"extras", "price_per_person"}
                for key, val in ej.items():
                    if key in _SKIP or not isinstance(val, dict):
                        continue
                    qty = int(val.get("qty", 1))
                    price = int(val.get("unit_price", 0)) * qty
                    label = key.replace("_", " ").capitalize() + (f" x{qty}" if qty > 1 else "")
                    extras_items.append((label, _fmt_clp(price)))

        extras_html = ""
        if extras_items:
            filas = "".join(
                f'<tr><td style="padding:4px 0;font-size:14px;color:#374151;">'
                f'· {name}</td>'
                f'<td style="padding:4px 0;font-size:14px;color:#374151;text-align:right;">'
                f'{price}</td></tr>'
                for name, price in extras_items
            )
            extras_html = (
                f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;">'
                f'<tr><td colspan="2" style="padding-bottom:6px;font-size:11px;font-weight:700;'
                f'color:#5fb8ae;text-transform:uppercase;letter-spacing:0.8px;">Extras incluidos</td></tr>'
                f'{filas}</table>'
            )

        pay_url = _get_woo_payment_link(str(row.payment_order_id).strip() if row.payment_order_id else None, email=email)
        extra_vars = {
            "servicio": row.servicio or "tu experiencia",
            "titulo_reserva": f"Experiencia HotBoat · {personas_str}",
            "fecha_reserva": fecha_str,
            "hora_reserva": hora_str,
            "personas": personas_str,
            "ingreso_total": total_fmt,
            "ingreso_reserva": reserva_fmt,
            "extras_html": extras_html,
            "pay_url": pay_url,
        }
        _send_email(session, auto, contact, trigger_key, extra_vars=extra_vars)


_BATCH_ORIGINS = {"Formulario T&C", "Sincronización HotBoat", ""}


def _check_welcome(auto: Automation, session: Session) -> None:
    """Fire welcome email to contacts created organically (popup/form), not batch imports."""
    config = auto.trigger_config or {}
    delay_hours = int(config.get("delay_hours", 0))
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
        # Skip contacts imported in batch (TC form, sync, CSV) — only fire for
        # organic signups via the popup/embed form (origin_utm is a URL or form name)
        origin = (contact.origin_utm or "").strip()
        if origin in _BATCH_ORIGINS or origin.startswith("Formulario #"):
            continue
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


def _normalize_categoria_cliente(cat: str) -> str | None:
    """Normaliza categoria_clientes (all_appointments) a familia / pareja / amigos."""
    c = (cat or "").strip().lower()
    if not c:
        return None
    if "familia" in c:
        return "familia"
    if "amigo" in c or "amigas" in c:
        return "amigos"
    if "pareja" in c:
        return "pareja"
    return None


def _normalize_tipo_cliente(tipo: str) -> str | None:
    """Normaliza tipo_clientes (all_appointments) a trabajador / empresario."""
    t = (tipo or "").strip().lower()
    if "trabaj" in t:
        return "trabajador"
    if "empres" in t:
        return "empresario"
    return None


def _resolve_appointment_from_booking_ref(booking_ref: str, src_engine):
    """
    Try 3 join strategies to find the booking in all_appointments.
      1. booking_ref = 'AA-{id}' → WHERE id = {number}
      2. TRIM(source_id) = booking_ref
      3. (legacy) hotboat_appointments.booking_ref (only if present)
    Returns a Row or None.
    """
    _COLS = """
        nombre_cliente, servicio, fecha, hora, ingreso_total,
        extras_json, customer_language, ciudad_origen, como_supieron,
        categoria_clientes, tipo_clientes
    """
    ref = (booking_ref or "").strip()
    if not ref:
        return None

    with src_engine.connect() as conn:
        # Strategy 1: AA-{number}
        m = re.match(r"^AA-(\d+)$", ref, re.IGNORECASE)
        if m:
            row = conn.execute(
                text(f"SELECT {_COLS} FROM all_appointments WHERE id = :id LIMIT 1"),
                {"id": int(m.group(1))},
            ).fetchone()
            if row:
                return row

        # Strategy 2: source_id match (web bookings)
        row = conn.execute(
            text(f"SELECT {_COLS} FROM all_appointments WHERE TRIM(source_id) = :ref ORDER BY created_at DESC LIMIT 1"),
            {"ref": ref},
        ).fetchone()
        if row:
            return row

        # Strategy 3: legacy hotboat_appointments table (if it exists)
        try:
            row = conn.execute(
                text(f"""
                    SELECT aa.nombre_cliente, aa.servicio, aa.fecha, aa.hora, aa.ingreso_total,
                           aa.extras_json, aa.customer_language, aa.ciudad_origen, aa.como_supieron,
                           aa.categoria_clientes, aa.tipo_clientes
                    FROM hotboat_appointments ha
                    JOIN all_appointments aa ON aa.source = 'hotboat' AND TRIM(aa.source_id) = ha.source_id
                    WHERE ha.booking_ref = :ref
                    ORDER BY aa.created_at DESC LIMIT 1
                """),
                {"ref": ref},
            ).fetchone()
            if row:
                return row
        except Exception:
            pass

    return None


def _check_tc_signatures(auto: Automation, session: Session) -> None:
    """
    5 hours after a T&C signature is created, resolve the associated booking,
    upsert the contact with enriched data (ticket, extras, location, language…)
    and optionally send an email if send_email=true in trigger_config.

    trigger_config:
      delay_hours   (default 5)   — minimum age of signature before processing
      lookback_hours (default 48) — how far back to scan for unprocessed sigs
      send_email    (default false)
    """
    config = auto.trigger_config or {}
    delay_hours = int(config.get("delay_hours", 5))
    lookback_hours = int(config.get("lookback_hours", 48))
    send_email = bool(config.get("send_email", False))

    now = datetime.utcnow()
    cutoff_recent = now - timedelta(hours=delay_hours)
    cutoff_old = now - timedelta(hours=delay_hours + lookback_hours)

    try:
        src = _source_engine()
        with src.connect() as conn:
            sigs = conn.execute(
                text("""
                    SELECT id, booking_ref, passenger_name, passenger_email,
                           passenger_phone, passenger_birthday
                    FROM hotboat_signatures
                    WHERE accepted_tc = true
                      AND passenger_email IS NOT NULL
                      AND passenger_email <> ''
                      AND created_at <= :recent
                      AND created_at >= :old
                    ORDER BY created_at
                """),
                {"recent": cutoff_recent, "old": cutoff_old},
            ).fetchall()
    except Exception as exc:
        logger.error("Automation %d tc_signature: cannot read source DB: %s", auto.id, exc)
        return

    for sig in sigs:
        trigger_key = f"tc_sig:{sig.id}"
        if _already_sent(session, auto.id, trigger_key):
            continue

        email = (sig.passenger_email or "").strip().lower()
        if not email or "@" not in email:
            continue

        appt = _resolve_appointment_from_booking_ref(sig.booking_ref, src)

        # ── Extract enrichment ────────────────────────────────────────────
        ultima_visita = None
        ticket_medio = None
        location = None
        language = None
        extras = None
        ha_alojamiento = False
        como_supieron = None
        categoria_cliente = None
        tipo_cliente = None

        if appt:
            ultima_visita = appt.fecha
            if appt.ingreso_total:
                ticket_medio = float(appt.ingreso_total)
            location = (appt.ciudad_origen or "").strip() or None
            language = (appt.customer_language or "").strip() or None
            if appt.extras_json and isinstance(appt.extras_json, dict):
                extras = [k for k in appt.extras_json if not k.startswith("aloj__")] or None
                ha_alojamiento = any(k.startswith("aloj__") for k in appt.extras_json)
            como_supieron = (appt.como_supieron or "").strip() or None
            categoria_cliente = _normalize_categoria_cliente(appt.categoria_clientes)
            tipo_cliente = _normalize_tipo_cliente(appt.tipo_clientes)

        # ── Upsert contact ────────────────────────────────────────────────
        now_dt = datetime.utcnow()
        name = (sig.passenger_name or "").strip() or None
        phone = (sig.passenger_phone or "").strip() or None
        birthday = sig.passenger_birthday

        existing = session.exec(select(Contact).where(Contact.email == email)).first()
        if existing:
            if name and not existing.name:
                existing.name = name
            if phone and not existing.phone:
                existing.phone = phone
            if birthday and not existing.birthday:
                existing.birthday = birthday
            if ultima_visita and (not existing.ultima_visita or ultima_visita > existing.ultima_visita):
                existing.ultima_visita = ultima_visita
            if ticket_medio and not existing.ticket_medio:
                existing.ticket_medio = ticket_medio
            if location and not existing.location:
                existing.location = location
            if language and not existing.language:
                existing.language = language
            if extras and not existing.extras_favoritos:
                existing.extras_favoritos = extras
            if ha_alojamiento:
                existing.ha_alojamiento = True
            cf = dict(existing.custom_fields or {})
            cf_changed = False
            if como_supieron and not cf.get("como_supieron"):
                cf["como_supieron"] = como_supieron
                cf_changed = True
            if categoria_cliente and not cf.get("categoria_cliente"):
                cf["categoria_cliente"] = categoria_cliente
                cf_changed = True
            if tipo_cliente and not cf.get("tipo_cliente"):
                cf["tipo_cliente"] = tipo_cliente
                cf_changed = True
            if cf_changed:
                existing.custom_fields = cf
            existing.opted_in = True
            if not existing.opted_in_at:
                existing.opted_in_at = now_dt
            existing.updated_at = now_dt
            session.add(existing)
            contact = existing
        else:
            cf = {}
            if como_supieron:
                cf["como_supieron"] = como_supieron
            if categoria_cliente:
                cf["categoria_cliente"] = categoria_cliente
            if tipo_cliente:
                cf["tipo_cliente"] = tipo_cliente
            contact = Contact(
                email=email,
                name=name,
                phone=phone,
                birthday=birthday,
                language=language or "es",
                origin_utm="Formulario T&C",
                location=location,
                custom_fields=cf or None,
                opted_in=True,
                opted_in_at=now_dt,
                veces_hotboat=1 if appt else 0,
                ultima_visita=ultima_visita,
                ha_alojamiento=ha_alojamiento,
                extras_favoritos=extras,
                ticket_medio=ticket_medio,
                created_at=now_dt,
                updated_at=now_dt,
            )
            session.add(contact)
            session.flush()  # get contact.id

        # ── Record run (dedup guard) ───────────────────────────────────────
        run = AutomationRun(
            automation_id=auto.id,
            contact_id=contact.id,
            contact_email=email,
            trigger_key=trigger_key,
            triggered_at=now_dt,
            executed_at=now_dt,
            status="sent",
        )
        session.add(run)

        # ── Optionally send email ─────────────────────────────────────────
        if send_email:
            _send_email(session, auto, contact, trigger_key)

        logger.info(
            "Automation %d tc_signature: processed sig %d → contact %s (appt=%s)",
            auto.id, sig.id, email, "found" if appt else "not found",
        )

    session.commit()


HANDLERS = {
    "abandoned_booking": _check_abandoned_booking,
    "welcome": _check_welcome,
    "post_visit": _check_post_visit,
    "reactivation": _check_reactivation,
    "tc_signature": _check_tc_signatures,
}


def _notify_campaign_reminder(campaign: Campaign) -> None:
    """Envía alerta a NOTIFY_EMAIL 24h antes del envío de una campaña."""
    if not settings.NOTIFY_EMAIL:
        return
    try:
        resend.api_key = settings.RESEND_API_KEY
        scheduled_str = campaign.scheduled_at.strftime("%d/%m/%Y %H:%M") if campaign.scheduled_at else "?"
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [settings.NOTIFY_EMAIL],
            "subject": f"⏰ Mañana se envía: {campaign.name}",
            "html": (
                f"<p>La campaña <strong>{campaign.name}</strong> está programada para mañana "
                f"a las <strong>{scheduled_str} UTC</strong>.</p>"
                f"<p>Si querés pausarla o modificarla, podés hacerlo desde "
                f"<a href='{settings.FRONTEND_URL}/campaigns/{campaign.id}'>el panel</a> "
                f"antes de que se dispare.</p>"
            ),
        })
        logger.info("Recordatorio enviado para campaña %d (%s)", campaign.id, campaign.name)
    except Exception as exc:
        logger.warning("No se pudo enviar recordatorio para campaña %d: %s", campaign.id, exc)


def _notify_campaign_fired(campaign: Campaign, contact_count: int) -> None:
    """Envía alerta a NOTIFY_EMAIL cuando una campaña comienza a enviarse."""
    if not settings.NOTIFY_EMAIL:
        return
    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.RESEND_FROM_EMAIL,
            "to": [settings.NOTIFY_EMAIL],
            "subject": f"🚀 Enviando ahora: {campaign.name}",
            "html": (
                f"<p>La campaña <strong>{campaign.name}</strong> acaba de comenzar su envío "
                f"a <strong>{contact_count}</strong> contactos.</p>"
                f"<p>Podés seguir el progreso en tiempo real en "
                f"<a href='{settings.FRONTEND_URL}/campaigns/{campaign.id}'>el panel</a>.</p>"
            ),
        })
    except Exception as exc:
        logger.warning("No se pudo enviar notificación de envío para campaña %d: %s", campaign.id, exc)


def run_campaign_reminders() -> None:
    """Detecta campañas programadas para las próximas 24h y envía recordatorio (una vez por campaña)."""
    with Session(db_engine) as session:
        now = datetime.utcnow()
        window_start = now + timedelta(hours=23)
        window_end = now + timedelta(hours=25)
        upcoming = session.exec(
            select(Campaign).where(
                Campaign.status == "scheduled",
                Campaign.scheduled_at >= window_start,
                Campaign.scheduled_at <= window_end,
            )
        ).all()
        for campaign in upcoming:
            if campaign.id not in _reminder_sent:
                _notify_campaign_reminder(campaign)
                _reminder_sent.add(campaign.id)


def run_scheduled_campaigns() -> None:
    """Fire campaigns whose scheduled_at has passed and are still in 'scheduled' status.
    Also retries campaigns stuck in 'sending' for more than 10 minutes (crash recovery)."""
    with Session(db_engine) as session:
        now = datetime.utcnow()
        due = session.exec(
            select(Campaign).where(
                Campaign.status == "scheduled",
                Campaign.scheduled_at <= now,
            )
        ).all()

        # Pick up campaigns stuck in 'sending' for > 10 min with no recent sends
        stuck_cutoff = now - timedelta(minutes=10)
        stuck = session.exec(
            select(Campaign).where(
                Campaign.status == "sending",
                Campaign.scheduled_at <= stuck_cutoff,
            )
        ).all()
        # Only retry if no CampaignSend was recorded in the last 10 min
        for c in stuck:
            recent_send = session.exec(
                select(CampaignSend).where(
                    CampaignSend.campaign_id == c.id,
                    CampaignSend.sent_at >= stuck_cutoff,
                )
            ).first()
            if not recent_send:
                logger.warning("Campaign %d stuck in 'sending' — resetting to 'scheduled' for retry", c.id)
                c.status = "scheduled"
                session.add(c)
                session.commit()
                due = list(due) + [c]
        for campaign in due:
            try:
                seg = session.get(Segment, campaign.segment_id)
                if not seg:
                    logger.warning("Scheduled campaign %d: segment %d not found", campaign.id, campaign.segment_id)
                    continue
                contacts = evaluate_segment(seg.conditions, session)
                if not contacts:
                    logger.warning("Scheduled campaign %d: no opted-in contacts", campaign.id)
                    continue
                already_sent = set(session.exec(
                    select(CampaignSend.contact_id).where(
                        CampaignSend.campaign_id == campaign.id,
                        CampaignSend.status != "failed",
                    )
                ).all())
                to_send = [c for c in contacts if c.id not in already_sent]
                if not to_send:
                    campaign.status = "sent"
                    session.add(campaign)
                    session.commit()
                    continue
                campaign.status = "sending"
                session.add(campaign)
                session.commit()
                contact_ids = [c.id for c in to_send]
                send_campaign_sync(campaign.id, contact_ids, len(contacts))
                logger.info("Scheduled campaign %d fired to %d contacts", campaign.id, len(contact_ids))
                _notify_campaign_fired(campaign, len(contact_ids))
            except Exception as exc:
                logger.exception("Scheduled campaign %d error: %s", campaign.id, exc)


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
                run_scheduled_campaigns()
                run_campaign_reminders()
            except Exception as exc:
                logger.exception("Automation scheduler error: %s", exc)
            time.sleep(60)  # 1 minute

    t = threading.Thread(target=loop, daemon=True, name="automation-scheduler")
    t.start()
    logger.info("Automation scheduler started (interval: 1 min)")
