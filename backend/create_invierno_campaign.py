"""
Crea la plantilla y campaña de Invierno 2026.
Uso: cd backend && python create_invierno_campaign.py

Envío programado: jueves 3 de julio a las 09:00 AM Chile (13:00 UTC).
Código: INVIERNO20 · Válido hasta el domingo 31 de julio.
"""
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.user import User      # noqa: registra tabla users para FK
from app.models.contact import Contact  # noqa: registra tabla contacts para FK
from app.models.template import Template
from app.models.campaign import Campaign
from app.models.segment import Segment

create_db_and_tables()

LOGO_URL = "https://hotboatchile.com/logo_hotboat_blanco.png"

SUBJECT = "{{nombre}}, el invierno en el agua es una experiencia diferente"
PREVIEW = "20% off + video gratis + foto enmarcada. Código INVIERNO20."

# Jueves 3 de julio, 09:00 AM Chile (UTC-4) = 13:00 UTC
SCHEDULED_AT = datetime(2026, 7, 3, 13, 0, 0)

HTML = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,700;0,800;0,900;1,400;1,700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#f0f7f6;">
<div style="font-family:'Playfair Display',Georgia,serif;max-width:600px;margin:0 auto;background:#ffffff;">

  <!-- Barra superior -->
  <div style="height:4px;background:#2f857c;"></div>

  <!-- Header -->
  <div style="padding:32px 48px;background:#235e58;">
    <img src="{LOGO_URL}" alt="HotBoat"
         style="height:72px;display:block;" />
  </div>

  <!-- Headline -->
  <div style="padding:48px 48px 32px;">
    <p style="margin:0 0 12px;font-size:12px;font-weight:600;letter-spacing:3px;color:#2f857c;text-transform:uppercase;">
      Invierno 2026 &middot; Válido hasta el 31 de julio
    </p>
    <h1 style="margin:0;font-size:38px;font-weight:900;color:#235e58;line-height:1.1;letter-spacing:-1px;">
      {{{{nombre}}}},<br>el invierno en el agua<br>
      <span style="color:#2f857c;">es otro nivel.</span>
    </h1>
  </div>

  <!-- Separador -->
  <div style="margin:0 48px;height:1px;background:#d6f0ee;"></div>

  <!-- Oferta editorial -->
  <div style="padding:32px 48px;">
    <p style="margin:0 0 28px;font-size:14px;color:#6b7280;font-weight:400;">
      Reserva este julio y te llevás todo esto incluido:
    </p>

    <div style="margin-bottom:24px;">
      <p style="margin:0 0 4px;font-size:22px;font-weight:700;color:#235e58;">20% de descuento</p>
      <p style="margin:0;font-size:14px;color:#6b7280;font-weight:400;">Directo sobre el precio de cualquier experiencia HotBoat.</p>
    </div>
    <div style="height:1px;background:#d6f0ee;margin-bottom:24px;"></div>

    <div style="margin-bottom:24px;">
      <p style="margin:0 0 4px;font-size:22px;font-weight:700;color:#235e58;">Foto enmarcada con Marco</p>
      <p style="margin:0;font-size:14px;color:#6b7280;font-weight:400;">Tu mejor momento del año, listo para colgar en casa. <span style="color:#2f857c;font-weight:600;">Gratis.</span></p>
    </div>
    <div style="height:1px;background:#d6f0ee;margin-bottom:24px;"></div>

    <div style="margin-bottom:8px;">
      <p style="margin:0 0 4px;font-size:22px;font-weight:700;color:#235e58;">Video profesional de dron</p>
      <p style="margin:0;font-size:14px;color:#6b7280;font-weight:400;">La experiencia filmada en HD para llevarte de recuerdo. <span style="color:#2f857c;font-weight:600;">Gratis.</span></p>
    </div>
  </div>

  <!-- Gift Card imagen -->
  <div style="margin:0 48px;padding:28px;background:#f0faf9;border-radius:4px;">
    <p style="margin:0 0 16px;font-size:12px;font-weight:600;letter-spacing:3px;color:#2f857c;text-transform:uppercase;">Y además llevás</p>
    <img src="https://hotboatchile.com/images/Gift%20Cards/giftcard-invierno.jpg"
         alt="Gift Card HotBoat" style="width:100%;border-radius:4px;display:block;margin-bottom:14px;" />
    <p style="margin:0;font-size:14px;color:#235e58;">
      Una <strong>gift card válida por 1 año.</strong> Para vos o para regalar cuando quieras.
    </p>
  </div>

  <!-- Código -->
  <div style="padding:40px 48px;text-align:center;">
    <p style="margin:0 0 16px;font-size:12px;letter-spacing:2px;color:#9ca3af;text-transform:uppercase;">Tu código de reserva</p>
    <div style="display:inline-block;border:2px solid #2f857c;padding:16px 40px;border-radius:2px;">
      <p style="margin:0;font-size:28px;font-weight:900;letter-spacing:6px;color:#2f857c;">INVIERNO20</p>
    </div>
    <p style="margin:12px 0 0;font-size:12px;color:#9ca3af;">Válido hasta el jueves 31 de julio de 2026</p>
  </div>

  <!-- CTA -->
  <div style="padding:0 48px 48px;text-align:center;">
    <a href="https://hotboat.cl"
       style="display:inline-block;background:#235e58;color:#ffffff;font-weight:700;font-size:15px;padding:16px 48px;border-radius:2px;text-decoration:none;letter-spacing:1px;text-transform:uppercase;">
      Reservar experiencia de invierno
    </a>
    <p style="margin:16px 0 0;font-size:12px;color:#9ca3af;">
      <a href="https://hotboat.cl" style="color:#2f857c;text-decoration:none;">hotboat.cl</a>
    </p>
  </div>

  <!-- Footer -->
  <div style="height:4px;background:#2f857c;"></div>
  <div style="padding:20px 48px;text-align:center;background:#f9fafb;">
    <p style="margin:0;font-size:11px;color:#9ca3af;">
      HotBoat &middot; Experiencias en el agua &middot; Chile &nbsp;&middot;&nbsp;
      <a href="##unsub##" style="color:#9ca3af;">Cancelar suscripción</a>
    </p>
  </div>

</div></body></html>"""

CAMP_NAME = "Invierno 2026 — Gift Card"

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
    print(f"   Envío    : {SCHEDULED_AT} UTC  →  jueves 3 jul 09:00 AM Chile")
    print(f"   Código   : INVIERNO20  (válido hasta 31 jul)")
    print()
    print("   Listo. El scheduler lo enviará automáticamente el jueves.")
