"""
Crea el template 'Invierno — Para los que vinieron en verano' y lo asigna
a la campaña [JUN] Oferta invernal — clientes solo verano.
Ejecutar: python seed_invierno_template.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from sqlmodel import Session, select, create_engine
from app.core.config import settings
from app.models.user import User          # noqa
from app.models.contact import Contact    # noqa
from app.models.segment import Segment    # noqa
from app.models.template import Template
from app.models.campaign import Campaign
from app.models.automation import Automation, AutomationRun  # noqa
from app.models.form import SignupForm    # noqa

engine = create_engine(settings.DATABASE_URL)

TEMPLATE_NAME = "Invierno — Para los que vinieron en verano"

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>El lago en invierno</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f4f8;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

          <!-- HEADER -->
          <tr>
            <td style="background-color:#0d2b45;padding:28px 40px;text-align:center;">
              <span style="color:#ffffff;font-size:22px;font-weight:700;letter-spacing:1px;">HotBoat</span>
            </td>
          </tr>

          <!-- HERO IMAGE PLACEHOLDER -->
          <tr>
            <td style="padding:0;">
              <img src="https://hotboat.cl/img/invierno-lago.jpg"
                   alt="El lago en invierno"
                   width="600"
                   style="width:100%;max-width:600px;display:block;height:300px;object-fit:cover;background-color:#b8cdd9;">
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:44px 48px 12px;">

              <!-- Saludo personal -->
              <p style="margin:0 0 24px;font-size:16px;color:#4a5568;line-height:1.6;">
                Hola {{ first_name }},
              </p>

              <!-- Headline -->
              <h1 style="margin:0 0 20px;font-size:28px;font-weight:800;color:#0d2b45;line-height:1.25;">
                El lago que conociste en verano<br>es otro en invierno.
              </h1>

              <!-- Párrafo 1 — gancho -->
              <p style="margin:0 0 20px;font-size:16px;color:#4a5568;line-height:1.7;">
                Te acordás del lago brillando, el calor, la energía de la temporada alta.
                Fue una experiencia increíble. Pero hay algo que la mayoría de la gente
                nunca descubre: <strong style="color:#0d2b45;">el lago en invierno
                es completamente diferente. Y para muchos de nuestros clientes,
                termina siendo su favorita.</strong>
              </p>

              <!-- Separador visual -->
              <hr style="border:none;border-top:2px solid #e2e8f0;margin:28px 0;">

              <!-- Tres razones — formato lista visual -->
              <p style="margin:0 0 16px;font-size:13px;font-weight:700;letter-spacing:2px;color:#0d2b45;text-transform:uppercase;">
                Por qué el invierno es distinto
              </p>

              <!-- Razón 1 -->
              <table cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                <tr>
                  <td style="width:40px;vertical-align:top;padding-top:2px;">
                    <span style="display:inline-block;width:28px;height:28px;border-radius:50%;background-color:#0d2b45;color:#ffffff;font-size:13px;font-weight:700;text-align:center;line-height:28px;">1</span>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="margin:0;font-size:16px;font-weight:700;color:#0d2b45;">El silencio real.</p>
                    <p style="margin:4px 0 0;font-size:15px;color:#4a5568;line-height:1.6;">
                      Sin multitudes. Sin ruido. Solo el agua, el viento y tu grupo.
                      En invierno la experiencia es tuya de verdad —
                      más íntima, más personal, más auténtica.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Razón 2 -->
              <table cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
                <tr>
                  <td style="width:40px;vertical-align:top;padding-top:2px;">
                    <span style="display:inline-block;width:28px;height:28px;border-radius:50%;background-color:#0d2b45;color:#ffffff;font-size:13px;font-weight:700;text-align:center;line-height:28px;">2</span>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="margin:0;font-size:16px;font-weight:700;color:#0d2b45;">Una belleza que el verano no tiene.</p>
                    <p style="margin:4px 0 0;font-size:15px;color:#4a5568;line-height:1.6;">
                      La niebla sobre el agua a primera hora. Los cerros nevados al fondo.
                      Los colores del otoño en las orillas. Es el mismo lago —
                      y al mismo tiempo, uno completamente nuevo.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Razón 3 -->
              <table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
                <tr>
                  <td style="width:40px;vertical-align:top;padding-top:2px;">
                    <span style="display:inline-block;width:28px;height:28px;border-radius:50%;background-color:#0d2b45;color:#ffffff;font-size:13px;font-weight:700;text-align:center;line-height:28px;">3</span>
                  </td>
                  <td style="padding-left:12px;">
                    <p style="margin:0;font-size:16px;font-weight:700;color:#0d2b45;">Toda nuestra atención para vos.</p>
                    <p style="margin:4px 0 0;font-size:15px;color:#4a5568;line-height:1.6;">
                      En temporada baja nuestro equipo tiene algo que en verano escasea:
                      tiempo. Más conversación, más detalle, más flexibilidad.
                      Los que vienen en invierno siempre nos dicen que se sintieron
                      como clientes VIP.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Separador -->
              <hr style="border:none;border-top:2px solid #e2e8f0;margin:28px 0;">

              <!-- Social proof -->
              <table cellpadding="0" cellspacing="0" style="background-color:#f7fafc;border-left:4px solid #0d2b45;border-radius:4px;padding:20px 24px;margin-bottom:28px;width:100%;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="margin:0;font-size:16px;font-style:italic;color:#2d3748;line-height:1.7;">
                      "Vine en verano y quedé encantada. Volví en julio por curiosidad
                      y fue completamente diferente — más tranquilo, más íntimo.
                      Ahora vengo en las dos temporadas."
                    </p>
                    <p style="margin:12px 0 0;font-size:13px;font-weight:700;color:#0d2b45;letter-spacing:0.5px;">
                      — Valentina R., clienta desde 2023
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Cierre de venta -->
              <p style="margin:0 0 20px;font-size:16px;color:#4a5568;line-height:1.7;">
                Los cupos de invierno son pocos — lo hacemos así a propósito,
                para que la experiencia siga siendo lo que tiene que ser.
                Si querés ser uno de los que descubren el lago en su versión
                más honesta, este es el momento.
              </p>

              <!-- CTA -->
              <table cellpadding="0" cellspacing="0" style="margin:32px 0;">
                <tr>
                  <td align="center" style="background-color:#0d2b45;border-radius:8px;padding:16px 40px;">
                    <a href="https://hotboat.cl/reservar"
                       style="color:#ffffff;font-size:16px;font-weight:700;text-decoration:none;letter-spacing:0.5px;">
                      Quiero vivir el lago en invierno →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- PS -->
              <p style="margin:0 0 40px;font-size:14px;color:#718096;line-height:1.6;">
                <strong>PD:</strong> Si ya tenés fecha en mente o querés que te ayudemos
                a armar el plan perfecto para un día de invierno en el lago,
                respondé este email — estamos para ayudarte.
              </p>

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#f7fafc;padding:24px 48px;border-top:1px solid #e2e8f0;text-align:center;">
              <p style="margin:0 0 8px;font-size:13px;color:#718096;">
                HotBoat — Experiencias en el lago
              </p>
              <p style="margin:0;font-size:12px;color:#a0aec0;">
                Recibís este email porque estuviste con nosotros.
                <a href="{{ unsubscribe_url }}" style="color:#a0aec0;">Darte de baja</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


def main():
    print("\n=== Template: Invierno — Para los que vinieron en verano ===\n")

    with Session(engine) as session:
        # Crear o actualizar el template
        existing = session.exec(
            select(Template).where(Template.name == TEMPLATE_NAME)
        ).first()

        if existing:
            existing.html_content = HTML
            existing.subject_default = "¿Sabías que el invierno tiene sus propias maravillas?"
            existing.preview_text = "El lago en invierno es todo lo que no te imaginás."
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            session.flush()
            tmpl_id = existing.id
            print(f"  ✓ Template actualizado (ID {tmpl_id})")
        else:
            tmpl = Template(
                name=TEMPLATE_NAME,
                subject_default="¿Sabías que el invierno tiene sus propias maravillas?",
                preview_text="El lago en invierno es todo lo que no te imaginás.",
                html_content=HTML,
            )
            session.add(tmpl)
            session.flush()
            tmpl_id = tmpl.id
            print(f"  + Template creado (ID {tmpl_id})")

        session.commit()

        # Asignar a la campaña de junio
        campaign = session.exec(
            select(Campaign).where(
                Campaign.name == "[JUN] Oferta invernal — clientes solo verano"
            )
        ).first()

        if campaign:
            campaign.template_id = tmpl_id
            campaign.subject = "¿Sabías que el invierno tiene sus propias maravillas?"
            campaign.preview_text = "El lago en invierno es todo lo que no te imaginás."
            session.add(campaign)
            session.commit()
            print(f"  ✓ Campaña ID {campaign.id} actualizada con el nuevo template")
        else:
            print("  ✗ Campaña '[JUN] Oferta invernal' no encontrada")

    print("\n=== Listo ===\n")


if __name__ == "__main__":
    main()
