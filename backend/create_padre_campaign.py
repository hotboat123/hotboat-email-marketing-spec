"""
Crea la plantilla y campaña de Día del Padre 2026.
Uso: cd backend && python create_padre_campaign.py

Envío programado: jueves 18 de junio a las 09:00 AM Chile (13:00 UTC).
Código: FELIZDIAPAPA · Válido hasta el domingo 21 de junio.
"""
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.user import User  # noqa: registra tabla users para FK
from app.models.contact import Contact  # noqa: registra tabla contacts para FK
from app.models.template import Template
from app.models.campaign import Campaign
from app.models.segment import Segment

create_db_and_tables()

LOGO_URL = "https://hotboatchile.com/logo_hotboat_blanco.png"

SUBJECT = "{{nombre}}, dale a tu papá una experiencia que no va a olvidar"
PREVIEW = "Video gratis + foto enmarcada + 20% off. Código FELIZDIAPAPA."

# Jueves 18 de junio, 09:00 AM Chile (UTC-4) = 13:00 UTC
SCHEDULED_AT = datetime(2026, 6, 18, 13, 0, 0)

FOOTER = """
<div style="border-top:1px solid #e5e7eb;margin-top:40px;padding-top:24px;text-align:center;">
  <p style="font-size:13px;font-weight:700;color:#111;margin:0 0 4px;">HotBoat</p>
  <p style="font-size:12px;color:#999;margin:4px 0;">Experiencias en el agua &middot; Chile</p>
  <p style="font-size:12px;color:#bbb;margin:8px 0;">
    <a href="##unsub##" style="color:#bbb;">Cancelar suscripci&oacute;n</a>
  </p>
</div>"""

HTML = f"""<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 24px;background:#ffffff;">

  <!-- Logo -->
  <div style="text-align:center;margin-bottom:36px;">
    <img src="{LOGO_URL}" alt="HotBoat" style="height:64px;width:auto;display:inline-block;" />
  </div>

  <!-- Saludo y titular -->
  <p style="font-size:17px;color:#444;line-height:1.6;margin:0 0 6px;">Hola {{{{nombre}}}},</p>
  <h1 style="font-size:26px;font-weight:800;color:#111;margin:0 0 12px;line-height:1.3;">
    Este Día del Padre,<br>regálale el lago ❤️
  </h1>
  <p style="font-size:16px;color:#555;line-height:1.75;margin:0 0 36px;">
    Más que un objeto, regálale un momento juntos en el agua.<br>
    Una experiencia HotBoat que van a recordar para siempre.
  </p>

  <!-- Gift Card Visual -->
  <div style="background:linear-gradient(135deg,#0c3b6e 0%,#1558a8 55%,#0ea5e9 100%);border-radius:20px;padding:36px 32px;margin:0 0 36px;overflow:hidden;position:relative;">

    <!-- Círculos decorativos -->
    <div style="position:absolute;top:-40px;right:-40px;width:140px;height:140px;border-radius:50%;background:rgba(255,255,255,0.06);"></div>
    <div style="position:absolute;bottom:-30px;left:-30px;width:100px;height:100px;border-radius:50%;background:rgba(255,255,255,0.05);"></div>

    <!-- Etiqueta Gift Card -->
    <div style="display:inline-block;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.3);border-radius:6px;padding:5px 13px;margin-bottom:22px;">
      <span style="color:#fff;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">🎁 Gift Card</span>
    </div>

    <!-- Para -->
    <p style="color:rgba(255,255,255,0.65);font-size:12px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 6px;">Para:</p>
    <p style="color:#ffffff;font-size:32px;font-weight:800;margin:0 0 22px;line-height:1.2;">Papá ❤️</p>

    <!-- Mensaje -->
    <div style="border-left:3px solid rgba(255,255,255,0.4);padding-left:18px;margin:0 0 24px;">
      <p style="color:rgba(255,255,255,0.92);font-size:16px;line-height:1.75;margin:0;font-style:italic;">
        "Te regalo una aventura en el agua.<br>
        Una experiencia HotBoat,<br>
        para los dos."
      </p>
    </div>

    <!-- Firma -->
    <p style="color:rgba(255,255,255,0.5);font-size:12px;font-weight:700;letter-spacing:2px;text-align:right;margin:0;text-transform:uppercase;">HOTBOAT</p>
  </div>

  <!-- Qué incluye -->
  <p style="font-size:12px;font-weight:700;color:#999;text-transform:uppercase;letter-spacing:1px;margin:0 0 14px;">La gift card incluye:</p>

  <div style="margin:0 0 32px;">

    <div style="display:flex;align-items:flex-start;gap:14px;background:#f8faff;border-radius:12px;padding:16px 18px;margin-bottom:10px;border:1px solid #e8f0fe;">
      <span style="font-size:28px;line-height:1;flex-shrink:0;">💰</span>
      <div>
        <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 2px;">20% de descuento</p>
        <p style="color:#666;font-size:13px;margin:0;">En cualquier experiencia HotBoat</p>
      </div>
    </div>

    <div style="display:flex;align-items:flex-start;gap:14px;background:#f8faff;border-radius:12px;padding:16px 18px;margin-bottom:10px;border:1px solid #e8f0fe;">
      <span style="font-size:28px;line-height:1;flex-shrink:0;">🎬</span>
      <div>
        <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 2px;">Video profesional gratis</p>
        <p style="color:#666;font-size:13px;margin:0;">Tu experiencia filmada en HD para llevar de recuerdo</p>
      </div>
    </div>

    <div style="display:flex;align-items:flex-start;gap:14px;background:#f8faff;border-radius:12px;padding:16px 18px;border:1px solid #e8f0fe;">
      <span style="font-size:28px;line-height:1;flex-shrink:0;">🖼️</span>
      <div>
        <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 2px;">Foto enmarcada con Marco</p>
        <p style="color:#666;font-size:13px;margin:0;">Un recuerdo familiar para llevar a casa</p>
      </div>
    </div>

  </div>

  <!-- Nota validez -->
  <p style="font-size:15px;color:#444;text-align:center;margin:0 0 28px;line-height:1.6;">
    🗓️ La gift card es válida para usar en <strong>cualquier fecha futura</strong>.<br>
    Sin apuro, cuando el papá quiera vivirla.
  </p>

  <!-- CTA -->
  <div style="text-align:center;margin:0 0 32px;">
    <a href="https://hotboat.cl" style="background:#2563eb;color:#ffffff;font-weight:800;padding:17px 52px;border-radius:13px;text-decoration:none;font-size:17px;display:inline-block;letter-spacing:0.2px;">
      Regalar experiencia 🎁
    </a>
  </div>

  <!-- Código de descuento -->
  <div style="background:#f0f7ff;border:2px dashed #93c5fd;border-radius:16px;padding:26px 24px;text-align:center;margin:0 0 32px;">
    <p style="font-size:13px;color:#555;margin:0 0 12px;font-weight:500;">Ingresa este código al reservar:</p>
    <div style="font-size:30px;font-weight:900;letter-spacing:3px;color:#1d4ed8;margin:0 0 10px;font-family:monospace;">FELIZDIAPAPA</div>
    <p style="font-size:12px;color:#888;margin:0;line-height:1.6;">
      ⏳ Válido hasta el <strong>domingo 21 de junio</strong><br>
      La experiencia se puede agendar para cualquier fecha posterior.
    </p>
  </div>

  <!-- Ayuda -->
  <p style="font-size:14px;color:#999;text-align:center;line-height:1.6;margin:0;">
    ¿Tienes dudas? Visita <a href="https://hotboat.cl" style="color:#2563eb;text-decoration:none;font-weight:600;">hotboat.cl</a> o escríbenos por WhatsApp.
  </p>

  {FOOTER}
</div>"""

CAMP_NAME = "Día del Padre 2026 — Gift Card"

with Session(engine) as session:
    # Segmento
    seg = session.exec(select(Segment).where(Segment.name == "Todos los suscriptores")).first()
    if not seg:
        print("❌  No se encontró el segmento 'Todos los suscriptores'. Créalo primero desde el panel.")
        raise SystemExit(1)

    now = datetime.utcnow()

    # Template
    existing_tpl = session.exec(select(Template).where(Template.name == CAMP_NAME)).first()
    if existing_tpl:
        existing_tpl.subject_default = SUBJECT
        existing_tpl.preview_text = PREVIEW
        existing_tpl.html_content = HTML
        existing_tpl.updated_at = now
        session.add(existing_tpl)
        session.flush()
        tpl_id = existing_tpl.id
        print(f"✓  Plantilla actualizada (id={tpl_id})")
    else:
        tpl = Template(
            name=CAMP_NAME,
            subject_default=SUBJECT,
            preview_text=PREVIEW,
            html_content=HTML,
            created_at=now,
            updated_at=now,
        )
        session.add(tpl)
        session.flush()
        tpl_id = tpl.id
        print(f"✓  Plantilla creada (id={tpl_id})")

    # Campaña
    existing_camp = session.exec(select(Campaign).where(Campaign.name == CAMP_NAME)).first()
    if existing_camp:
        existing_camp.subject = SUBJECT
        existing_camp.template_id = tpl_id
        existing_camp.segment_id = seg.id
        existing_camp.scheduled_at = SCHEDULED_AT
        existing_camp.status = "scheduled"
        session.add(existing_camp)
        print(f"✓  Campaña actualizada (id={existing_camp.id})")
    else:
        camp = Campaign(
            name=CAMP_NAME,
            subject=SUBJECT,
            template_id=tpl_id,
            segment_id=seg.id,
            status="scheduled",
            scheduled_at=SCHEDULED_AT,
            created_at=now,
        )
        session.add(camp)
        print("✓  Campaña creada")

    session.commit()
    print()
    print(f"   Segmento : {seg.name} (id={seg.id})")
    print(f"   Envío    : {SCHEDULED_AT} UTC  →  jueves 18 jun 09:00 AM Chile")
    print(f"   Código   : FELIZDIAPAPA  (válido hasta 21 jun)")
    print()
    print("   Listo. El scheduler lo enviará automáticamente el jueves.")
