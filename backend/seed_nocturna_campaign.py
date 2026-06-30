"""
Crea la plantilla y campaña HotBoat Nocturna — Julio 2026.
Uso: cd backend && python seed_nocturna_campaign.py

Reemplazar FOTO_NOCTURNA_URL con la URL real de la foto antes de ejecutar.
Envío programado: martes 1 de julio a las 09:00 AM Chile (13:00 UTC).
"""
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.user import User      # noqa
from app.models.contact import Contact  # noqa
from app.models.template import Template
from app.models.campaign import Campaign
from app.models.segment import Segment

create_db_and_tables()

# ── Reemplazá esto con la URL de tu foto de luna llena ──────────────────────
FOTO_NOCTURNA_URL = "https://hotboatchile.com/images/nocturna-luna-llena.jpg"
# ────────────────────────────────────────────────────────────────────────────

LOGO_URL = "https://hotboatchile.com/logo_hotboat_blanco.png"

CAMP_NAME = "HotBoat Nocturna — Julio 2026"
SUBJECT   = "{{nombre}}, la noche en el lago es una experiencia diferente"
PREVIEW   = "Mejoras para el frío + tabla de picoteo gratis. Viví HotBoat de noche."

# Martes 1 de julio, 09:00 AM Chile (UTC-4) = 13:00 UTC
SCHEDULED_AT = datetime(2026, 7, 1, 13, 0, 0)

HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f0f7f6;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f7f6;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(35,94,88,0.10);">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#235e58;padding:28px 40px;text-align:center;">
              <img src="{LOGO_URL}" alt="HotBoat" style="height:56px;display:block;margin:0 auto;" />
            </td>
          </tr>

          <!-- HERO FOTO NOCTURNA -->
          <tr>
            <td style="padding:0;">
              <img src="{FOTO_NOCTURNA_URL}"
                   alt="HotBoat nocturna — luna llena sobre el lago"
                   width="600"
                   style="width:100%;max-width:600px;display:block;height:320px;object-fit:cover;background-color:#1a3a38;">
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:44px 48px 12px;">

              <!-- Saludo -->
              <p style="margin:0 0 24px;font-size:16px;color:#4a5568;line-height:1.6;">
                Hola <strong style="color:#235e58;">{{{{nombre}}}}</strong>,
              </p>

              <!-- Headline -->
              <h1 style="margin:0 0 20px;font-size:28px;font-weight:800;color:#235e58;line-height:1.25;">
                El lago de noche<br>es una experiencia completamente diferente.
              </h1>

              <!-- Párrafo gancho -->
              <p style="margin:0 0 20px;font-size:16px;color:#4a5568;line-height:1.7;">
                El agua quieta, el cielo abierto, las luces del pueblo reflejándose en el lago.
                Hay algo en la experiencia nocturna de HotBoat que es muy difícil de describir
                — y muy fácil de sentir. <strong style="color:#235e58;">La mayoría de nuestros
                clientes nos dice que fue la versión más especial de todas.</strong>
              </p>

              <!-- Separador -->
              <hr style="border:none;border-top:2px solid #d6f0ee;margin:28px 0;">

              <!-- Sección mejoras frío -->
              <p style="margin:0 0 16px;font-size:13px;font-weight:700;letter-spacing:2px;color:#235e58;text-transform:uppercase;">
                Lo que hicimos para que no pases frío
              </p>

              <!-- Mejora 1 -->
              <table cellpadding="0" cellspacing="0" style="margin-bottom:20px;width:100%;">
                <tr>
                  <td style="width:40px;vertical-align:top;padding-top:2px;">
                    <span style="display:inline-block;width:28px;height:28px;border-radius:50%;background-color:#235e58;color:#ffffff;font-size:13px;font-weight:700;text-align:center;line-height:28px;">1</span>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="margin:0;font-size:16px;font-weight:700;color:#235e58;">Mantas térmicas para cada pasajero.</p>
                    <p style="margin:4px 0 0;font-size:15px;color:#4a5568;line-height:1.6;">
                      Sumamos más mantas a bordo para que cada persona tenga la suya
                      durante toda la experiencia. Nada de pasarse frío esperando turno.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Mejora 2 -->
              <table cellpadding="0" cellspacing="0" style="margin-bottom:20px;width:100%;">
                <tr>
                  <td style="width:40px;vertical-align:top;padding-top:2px;">
                    <span style="display:inline-block;width:28px;height:28px;border-radius:50%;background-color:#235e58;color:#ffffff;font-size:13px;font-weight:700;text-align:center;line-height:28px;">2</span>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="margin:0;font-size:16px;font-weight:700;color:#235e58;">Bebidas calientes a bordo.</p>
                    <p style="margin:4px 0 0;font-size:15px;color:#4a5568;line-height:1.6;">
                      Thermos con té y café disponibles durante toda la salida.
                      Nada mejor que una bebida caliente mirando el lago de noche.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Mejora 3 -->
              <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;width:100%;">
                <tr>
                  <td style="width:40px;vertical-align:top;padding-top:2px;">
                    <span style="display:inline-block;width:28px;height:28px;border-radius:50%;background-color:#235e58;color:#ffffff;font-size:13px;font-weight:700;text-align:center;line-height:28px;">3</span>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="margin:0;font-size:16px;font-weight:700;color:#235e58;">Capas cortaviento disponibles.</p>
                    <p style="margin:4px 0 0;font-size:15px;color:#4a5568;line-height:1.6;">
                      Tenemos capas impermeables a bordo para quien las necesite.
                      Salís preparado sin importar cómo venga el viento.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Separador -->
              <hr style="border:none;border-top:2px solid #d6f0ee;margin:28px 0;">

              <!-- Tabla de picoteo GRATIS — destacado -->
              <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:28px;">
                <tr>
                  <td style="background-color:#f0faf9;border-left:4px solid #2f857c;border-radius:0 8px 8px 0;padding:20px 24px;">
                    <p style="margin:0 0 6px;font-size:13px;font-weight:700;letter-spacing:1.5px;color:#2f857c;text-transform:uppercase;">Incluido sin costo extra</p>
                    <p style="margin:0 0 6px;font-size:20px;font-weight:800;color:#235e58;">🧀 Tabla de picoteo gratis</p>
                    <p style="margin:0;font-size:15px;color:#4a5568;line-height:1.6;">
                      Para que la experiencia sea completa, cada salida nocturna incluye
                      una tabla de picoteo para compartir a bordo. Sin costo adicional.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Cita -->
              <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;width:100%;">
                <tr>
                  <td style="background-color:#f7fafc;border-left:4px solid #235e58;border-radius:0 8px 8px 0;padding:20px 24px;">
                    <p style="margin:0 0 12px;font-size:16px;font-style:italic;color:#2d3748;line-height:1.7;">
                      "Ya sea con luna llena, noche de estrellas fugaces o noche lluviosa,
                      estaremos recibiendo gente para que viva esta hermosa experiencia nocturna."
                    </p>
                    <p style="margin:0;font-size:13px;font-weight:700;color:#235e58;letter-spacing:0.5px;">
                      — El equipo HotBoat
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Cierre -->
              <p style="margin:0 0 20px;font-size:16px;color:#4a5568;line-height:1.7;">
                Los cupos nocturnos son limitados y se llenan rápido — especialmente
                las noches de luna llena. Si tenés una fecha en mente, no lo dejes para después.
              </p>

              <!-- CTA -->
              <table cellpadding="0" cellspacing="0" style="margin:32px 0;">
                <tr>
                  <td align="center" style="background-color:#235e58;border-radius:8px;padding:16px 40px;">
                    <a href="https://hotboat.cl"
                       style="color:#ffffff;font-size:16px;font-weight:700;text-decoration:none;letter-spacing:0.5px;">
                      Quiero vivir el lago de noche &#x2192;
                    </a>
                  </td>
                </tr>
              </table>

              <!-- PD -->
              <p style="margin:0 0 40px;font-size:14px;color:#718096;line-height:1.6;">
                <strong>PD:</strong> Si tenés preguntas sobre la experiencia nocturna o
                querés saber qué fechas tenemos disponibles, respondé este email
                o escribinos por <a href="https://wa.me/56950456090" style="color:#235e58;font-weight:600;">WhatsApp</a>.
                Estamos para ayudarte.
              </p>

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#f7fafc;padding:24px 48px;border-top:1px solid #d6f0ee;text-align:center;">
              <p style="margin:0 0 8px;font-size:13px;color:#718096;">
                HotBoat &middot; Experiencias en el agua &middot; Chile
              </p>
              <p style="margin:0;font-size:12px;color:#a0aec0;">
                Recibiste este email porque estuviste con nosotros o te suscribiste a nuestras novedades.<br>
                <a href="##unsub##" style="color:#a0aec0;">Cancelar suscripci&#243;n</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


with Session(engine) as session:
    seg = session.exec(select(Segment).where(Segment.name == "Todos los suscriptores")).first()
    if not seg:
        print("❌  No se encontró el segmento 'Todos los suscriptores'.")
        raise SystemExit(1)

    now = datetime.utcnow()

    # Template
    existing_tpl = session.exec(select(Template).where(Template.name == CAMP_NAME)).first()
    if existing_tpl:
        existing_tpl.subject_default = SUBJECT
        existing_tpl.preview_text    = PREVIEW
        existing_tpl.html_content    = HTML
        existing_tpl.updated_at      = now
        session.add(existing_tpl)
        session.flush()
        tpl_id = existing_tpl.id
        print(f"✓  Plantilla actualizada (id={tpl_id})")
    else:
        tpl = Template(name=CAMP_NAME, subject_default=SUBJECT,
                       preview_text=PREVIEW, html_content=HTML,
                       created_at=now, updated_at=now)
        session.add(tpl)
        session.flush()
        tpl_id = tpl.id
        print(f"✓  Plantilla creada (id={tpl_id})")

    # Campaña
    existing_camp = session.exec(select(Campaign).where(Campaign.name == CAMP_NAME)).first()
    if existing_camp:
        existing_camp.subject      = SUBJECT
        existing_camp.template_id  = tpl_id
        existing_camp.segment_id   = seg.id
        existing_camp.scheduled_at = SCHEDULED_AT
        existing_camp.status       = "scheduled"
        session.add(existing_camp)
        print(f"✓  Campaña actualizada (id={existing_camp.id})")
    else:
        camp = Campaign(name=CAMP_NAME, subject=SUBJECT, template_id=tpl_id,
                        segment_id=seg.id, status="scheduled",
                        scheduled_at=SCHEDULED_AT, created_at=now)
        session.add(camp)
        print("✓  Campaña creada")

    session.commit()
    print()
    print(f"   Segmento : {seg.name} (id={seg.id})")
    print(f"   Envío    : {SCHEDULED_AT} UTC  →  martes 1 jul 09:00 AM Chile")
    print()
    print("   ⚠️  Acordate de actualizar FOTO_NOCTURNA_URL antes de ejecutar.")
    print("   Listo. El scheduler lo enviará automáticamente el martes.")
