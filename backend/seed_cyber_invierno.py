"""
Crea template + campaña del Cyber Tardío HotBoat 2026 — rediseño premium.
Ejecutar: python seed_cyber_invierno.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from sqlmodel import Session, select, create_engine
from app.core.config import settings
from app.models.user import User; from app.models.contact import Contact
from app.models.segment import Segment; from app.models.template import Template
from app.models.campaign import Campaign
from app.models.automation import Automation, AutomationRun
from app.models.form import SignupForm

engine = create_engine(settings.DATABASE_URL)

TEMPLATE_NAME = "Cyber Tardío — Foto + Dron + 10% off"

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background-color:#040f1c;">

<div style="font-family:'DM Sans',Inter,Arial,sans-serif;max-width:600px;margin:0 auto;background:#040f1c;">

  <!-- ═══ HERO ══════════════════════════════════════════════════════════════ -->
  <div style="background:linear-gradient(160deg,#071a2e 0%,#0a1f38 60%,#071628 100%);padding:48px 40px 40px;text-align:center;border-bottom:1px solid rgba(0,200,255,0.12);">

    <img src="https://hotboatchile.com/logo_hotboat_blanco.png"
         alt="HotBoat"
         style="height:72px;width:auto;display:block;margin:0 auto 28px;" />

    <!-- Línea decorativa -->
    <div style="width:48px;height:3px;background:linear-gradient(90deg,#00c8ff,#f59e0b);margin:0 auto 28px;border-radius:99px;"></div>

    <h1 style="margin:0 0 12px;color:#ffffff;font-size:26px;font-weight:900;line-height:1.25;letter-spacing:-0.5px;">
      Llegamos tarde al Cyber.<br>
      <span style="color:#00c8ff;">Lo hicimos de todas formas.</span>
    </h1>

    <p style="margin:0;color:#7fa8c8;font-size:15px;font-weight:500;">
      {{ nombre or 'Hola' }}, preparamos algo que vale la pena.
    </p>
  </div>

  <!-- ═══ INTRO ════════════════════════════════════════════════════════════ -->
  <div style="padding:32px 40px 8px;text-align:center;">
    <p style="margin:0;color:#94a3b8;font-size:15px;line-height:1.7;">
      Reservá antes del <strong style="color:#ffffff;">domingo 7 de junio</strong> y te regalamos:
    </p>
  </div>

  <!-- ═══ BENEFICIOS ═══════════════════════════════════════════════════════ -->
  <div style="padding:20px 40px 8px;">

    <!-- Beneficio 1: Foto -->
    <div style="background:#0c1e33;border:1px solid rgba(0,200,255,0.18);border-left:3px solid #00c8ff;border-radius:12px;padding:18px 20px;margin-bottom:12px;display:flex;align-items:center;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="width:44px;vertical-align:middle;">
            <div style="width:40px;height:40px;background:rgba(0,200,255,0.12);border-radius:10px;text-align:center;line-height:40px;font-size:20px;">📸</div>
          </td>
          <td style="padding-left:14px;vertical-align:middle;">
            <p style="margin:0;color:#ffffff;font-size:15px;font-weight:700;">Foto con marco</p>
            <p style="margin:2px 0 0;color:#7fa8c8;font-size:13px;">Tu mejor momento del día, enmarcado.</p>
          </td>
          <td style="text-align:right;vertical-align:middle;white-space:nowrap;">
            <span style="background:rgba(0,200,255,0.12);color:#00c8ff;font-size:11px;font-weight:800;letter-spacing:1px;padding:4px 10px;border-radius:99px;border:1px solid rgba(0,200,255,0.3);">GRATIS</span>
          </td>
        </tr>
      </table>
    </div>

    <!-- Beneficio 2: Dron -->
    <div style="background:#0c1e33;border:1px solid rgba(0,200,255,0.18);border-left:3px solid #00c8ff;border-radius:12px;padding:18px 20px;margin-bottom:12px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="width:44px;vertical-align:middle;">
            <div style="width:40px;height:40px;background:rgba(0,200,255,0.12);border-radius:10px;text-align:center;line-height:40px;font-size:20px;">🚁</div>
          </td>
          <td style="padding-left:14px;vertical-align:middle;">
            <p style="margin:0;color:#ffffff;font-size:15px;font-weight:700;">Video de dron</p>
            <p style="margin:2px 0 0;color:#7fa8c8;font-size:13px;">Visto desde el cielo, en video profesional.</p>
          </td>
          <td style="text-align:right;vertical-align:middle;white-space:nowrap;">
            <span style="background:rgba(0,200,255,0.12);color:#00c8ff;font-size:11px;font-weight:800;letter-spacing:1px;padding:4px 10px;border-radius:99px;border:1px solid rgba(0,200,255,0.3);">GRATIS</span>
          </td>
        </tr>
      </table>
    </div>

    <!-- Beneficio 3: Descuento (acento dorado) -->
    <div style="background:#0c1e33;border:1px solid rgba(245,158,11,0.2);border-left:3px solid #f59e0b;border-radius:12px;padding:18px 20px;margin-bottom:8px;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="width:44px;vertical-align:middle;">
            <div style="width:40px;height:40px;background:rgba(245,158,11,0.12);border-radius:10px;text-align:center;line-height:40px;font-size:20px;">💸</div>
          </td>
          <td style="padding-left:14px;vertical-align:middle;">
            <p style="margin:0;color:#ffffff;font-size:15px;font-weight:700;">10% de descuento</p>
            <p style="margin:2px 0 0;color:#7fa8c8;font-size:13px;">Directo en tu reserva, sin vueltas.</p>
          </td>
          <td style="text-align:right;vertical-align:middle;white-space:nowrap;">
            <span style="background:rgba(245,158,11,0.12);color:#f59e0b;font-size:11px;font-weight:800;letter-spacing:1px;padding:4px 10px;border-radius:99px;border:1px solid rgba(245,158,11,0.3);">INCLUIDO</span>
          </td>
        </tr>
      </table>
    </div>

  </div>

  <!-- ═══ SEPARADOR ════════════════════════════════════════════════════════ -->
  <div style="padding:24px 40px;">
    <div style="height:1px;background:linear-gradient(90deg,transparent,rgba(0,200,255,0.2),transparent);"></div>
  </div>

  <!-- ═══ GIFT CARD ════════════════════════════════════════════════════════ -->
  <div style="padding:0 40px 32px;text-align:center;">
    <p style="margin:0 0 6px;color:#7fa8c8;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Y además</p>
    <p style="margin:0 0 20px;color:#ffffff;font-size:18px;font-weight:800;">Llevás una gift card válida por 1 año</p>

    <!-- Marco con glow -->
    <div style="display:inline-block;border-radius:14px;padding:3px;background:linear-gradient(135deg,#00c8ff,#f59e0b,#00c8ff);box-shadow:0 0 32px rgba(0,200,255,0.2);">
      <div style="border-radius:12px;overflow:hidden;background:#0c1e33;">
        <img src="https://hotboatchile.com/images/Gift%20Cards/Gift%20Card%20example%201.jpg"
             alt="Gift Card HotBoat"
             style="width:100%;max-width:460px;display:block;border-radius:12px;" />
      </div>
    </div>

    <p style="margin:16px 0 0;color:#94a3b8;font-size:14px;line-height:1.6;">
      Para usarla cuando quieras, o para regalarle a alguien especial.
    </p>
  </div>

  <!-- ═══ CUPÓN ════════════════════════════════════════════════════════════ -->
  <div style="padding:0 40px 32px;text-align:center;">
    <p style="margin:0 0 14px;color:#7fa8c8;font-size:13px;">Ingresá este código al reservar:</p>

    <div style="display:inline-block;border:1px solid rgba(0,200,255,0.4);border-radius:14px;padding:3px;box-shadow:0 0 24px rgba(0,200,255,0.12);">
      <div style="background:#071a2e;border-radius:12px;padding:20px 48px;">
        <p style="margin:0 0 4px;font-size:10px;font-weight:700;letter-spacing:3px;color:#7fa8c8;text-transform:uppercase;">Código de reserva</p>
        <p style="margin:0;font-size:32px;font-weight:900;letter-spacing:6px;color:#00c8ff;line-height:1.15;">CYBERINVIERNO</p>
      </div>
    </div>

    <p style="margin:12px 0 0;color:#4a6a85;font-size:12px;">
      Válido hasta el domingo 7 de junio de 2026
    </p>
  </div>

  <!-- ═══ CTA ═══════════════════════════════════════════════════════════════ -->
  <div style="padding:0 40px 16px;text-align:center;">
    <a href="https://whatsapp.hotboat.cl/booking"
       style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#f97316);color:#ffffff;font-weight:800;font-size:16px;padding:18px 52px;border-radius:12px;text-decoration:none;letter-spacing:0.3px;box-shadow:0 4px 24px rgba(245,158,11,0.35);">
      Reservar ahora &nbsp;🌊
    </a>
  </div>

  <div style="padding:0 40px 40px;text-align:center;">
    <a href="https://hotboat.cl"
       style="color:#4a6a85;font-size:13px;text-decoration:none;">
      Ver toda la experiencia en hotboat.cl
    </a>
  </div>

  <!-- ═══ FOOTER ════════════════════════════════════════════════════════════ -->
  <div style="border-top:1px solid rgba(255,255,255,0.06);padding:24px 40px;text-align:center;background:#040f1c;">
    <p style="margin:0 0 4px;font-size:13px;font-weight:700;color:#4a6a85;">HotBoat</p>
    <p style="margin:0 0 10px;font-size:12px;color:#2d4a62;">Experiencias en el agua &middot; Chile</p>
    <a href="{{ unsubscribe_url }}" style="font-size:11px;color:#2d4a62;text-decoration:underline;">Cancelar suscripción</a>
  </div>

</div>
</body>
</html>"""


def main():
    print("=== Cyber Tardio HotBoat 2026 — rediseno premium ===")
    with Session(engine) as session:

        # Template
        existing_tmpl = session.exec(
            select(Template).where(Template.name == TEMPLATE_NAME)
        ).first()
        if existing_tmpl:
            existing_tmpl.html_content = HTML
            existing_tmpl.updated_at = datetime.utcnow()
            session.add(existing_tmpl)
            session.flush()
            tmpl_id = existing_tmpl.id
            print(f"  Template actualizado (ID {tmpl_id})")
        else:
            tmpl = Template(
                name=TEMPLATE_NAME,
                subject_default="Llegamos tarde al Cyber. Lo hicimos de todas formas.",
                preview_text="Foto con marco + video de dron gratis. Codigo CYBERINVIERNO, hasta el domingo.",
                html_content=HTML,
            )
            session.add(tmpl)
            session.flush()
            tmpl_id = tmpl.id
            print(f"  Template creado (ID {tmpl_id})")
        session.commit()

        # Preview local
        from jinja2 import Template as JTemplate
        rendered = JTemplate(HTML).render(nombre="Tomas", unsubscribe_url="#")
        preview_path = os.path.join(os.path.dirname(__file__), "preview_cyber_invierno.html")
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"  Preview: {preview_path}")

    print("=== Listo ===")


if __name__ == "__main__":
    main()
