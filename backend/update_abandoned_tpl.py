"""Actualiza el HTML de la plantilla 32 (Carrito abandonado) con los nuevos colores de marca."""
import psycopg2
from datetime import datetime

DB = "postgresql://postgres:mcxQvhpGaatBzcZNCbVqnGWGBjQpCNYJ@turntable.proxy.rlwy.net:48129/railway"

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
</head>
<body style="margin:0;padding:0;background:#f0f7f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7f6;padding:40px 16px;">
<tr><td align="center">

  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 4px 24px rgba(35,94,88,0.10);">

    <!-- HEADER -->
    <tr>
      <td style="background:linear-gradient(135deg,#2f857c 0%,#246b64 100%);padding:44px 48px 36px;text-align:center;">
        <img src="https://hotboatchile.com/logo_hotboat_blanco.png"
             alt="HotBoat" width="130"
             style="display:block;margin:0 auto 28px;height:auto;" />
        <div style="display:inline-block;background:rgba(255,255,255,0.15);border-radius:50px;padding:6px 18px;margin-bottom:20px;">
          <span style="color:rgba(255,255,255,0.9);font-size:12px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;">Reserva pendiente</span>
        </div>
        <h1 style="color:#ffffff;font-size:28px;font-weight:800;margin:0 0 10px;line-height:1.25;">
          {{nombre}}, dejaste algo atras &#x1F6DF;
        </h1>
        <p style="color:rgba(255,255,255,0.85);font-size:16px;margin:0;line-height:1.5;">
          Tu reserva en HotBoat esta esperandote.
        </p>
      </td>
    </tr>

    <!-- CUERPO -->
    <tr>
      <td style="padding:40px 48px 0;">

        <p style="font-size:16px;color:#374151;line-height:1.7;margin:0 0 28px;">
          Hola <strong style="color:#235e58;">{{nombre}}</strong>, vimos que casi completaste tu reserva
          pero algo te interrumpio. Sin problema: todo sigue guardado y listo para que termines en segundos.
        </p>

        <!-- Tarjeta de reserva -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0faf9;border:1.5px solid #aedfdb;border-radius:14px;overflow:hidden;margin-bottom:28px;">
          <tr>
            <td style="background:#235e58;padding:14px 20px;">
              <p style="margin:0;color:#ffffff;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Detalle de tu reserva</p>
            </td>
          </tr>
          <tr>
            <td style="padding:20px;">
              <table width="100%" cellpadding="0" cellspacing="0">

                <!-- Servicio -->
                <tr>
                  <td style="padding:10px 0;border-bottom:1px solid #d6f0ee;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="width:28px;vertical-align:middle;font-size:18px;">&#x1F6A4;</td>
                        <td style="vertical-align:middle;padding-left:8px;">
                          <p style="margin:0;font-size:11px;color:#5fb8ae;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;">Experiencia</p>
                          <p style="margin:3px 0 0;font-size:15px;color:#235e58;font-weight:700;">{{servicio}}</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- Fecha / Hora -->
                <tr>
                  <td style="padding:10px 0;border-bottom:1px solid #d6f0ee;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td width="50%" style="vertical-align:top;padding-right:12px;">
                          <p style="margin:0;font-size:11px;color:#5fb8ae;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;">&#x1F4C5; Fecha</p>
                          <p style="margin:3px 0 0;font-size:15px;color:#235e58;font-weight:700;">{{fecha_reserva}}</p>
                        </td>
                        <td width="50%" style="vertical-align:top;">
                          <p style="margin:0;font-size:11px;color:#5fb8ae;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;">&#x1F550; Hora</p>
                          <p style="margin:3px 0 0;font-size:15px;color:#235e58;font-weight:700;">{{hora_reserva}} hrs</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- Personas -->
                <tr>
                  <td style="padding:10px 0;border-bottom:1px solid #d6f0ee;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="width:28px;vertical-align:middle;font-size:18px;">&#x1F465;</td>
                        <td style="vertical-align:middle;padding-left:8px;">
                          <p style="margin:0;font-size:11px;color:#5fb8ae;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;">Pasajeros</p>
                          <p style="margin:3px 0 0;font-size:15px;color:#235e58;font-weight:700;">{{personas}}</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- Total -->
                <tr>
                  <td style="padding:14px 0 4px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="vertical-align:middle;">
                          <p style="margin:0;font-size:13px;color:#6b7280;">Total a pagar</p>
                        </td>
                        <td style="text-align:right;vertical-align:middle;">
                          <p style="margin:0;font-size:24px;font-weight:900;color:#235e58;">{{ingreso_total}}</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

              </table>
            </td>
          </tr>
        </table>

        <!-- Urgencia -->
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#fff8ee;border:1.5px solid #e0c090;border-radius:12px;margin-bottom:32px;">
          <tr>
            <td style="padding:16px 20px;">
              <p style="margin:0;font-size:14px;color:#7a5520;line-height:1.6;">
                &#x23F3; <strong>Los cupos son limitados.</strong> No podemos garantizar disponibilidad para tu fecha si no confirmas pronto.
              </p>
            </td>
          </tr>
        </table>

        <!-- CTA -->
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
          <tr>
            <td align="center">
              <a href="{{pay_url}}"
                 style="display:inline-block;background:linear-gradient(135deg,#c98a3c 0%,#a86d28 100%);color:#ffffff;font-weight:800;font-size:16px;padding:17px 52px;border-radius:12px;text-decoration:none;letter-spacing:0.3px;">
                Completar mi reserva &#x2192;
              </a>
            </td>
          </tr>
        </table>

        <p style="text-align:center;font-size:13px;color:#9ca3af;margin:0 0 8px;">
          Tienes dudas? Responde este email o escribenos por
          <a href="https://wa.me/56950456090" style="color:#34897f;text-decoration:none;font-weight:600;">WhatsApp</a>.
        </p>

      </td>
    </tr>

    <!-- SEPARADOR -->
    <tr>
      <td style="padding:36px 48px 0;">
        <div style="border-top:1px solid #e5e7eb;"></div>
      </td>
    </tr>

    <!-- FOOTER -->
    <tr>
      <td style="padding:24px 48px 36px;text-align:center;">
        <p style="margin:0 0 4px;font-size:13px;font-weight:700;color:#235e58;">HotBoat</p>
        <p style="margin:0 0 12px;font-size:12px;color:#9ca3af;">Experiencias en el agua &middot; Chile</p>
        <p style="margin:0;font-size:11px;color:#c4c4c4;line-height:1.8;">
          Recibiste este email porque iniciaste una reserva en hotboat.cl.<br>
          <a href="https://hotboat.cl/unsubscribe?email={{email}}" style="color:#c4c4c4;text-decoration:underline;">Cancelar suscripcion</a>
        </p>
      </td>
    </tr>

  </table>
</td></tr>
</table>

</body>
</html>"""

conn = psycopg2.connect(DB)
cur = conn.cursor()
cur.execute(
    "UPDATE templates SET html_content = %s, updated_at = %s WHERE id = 32",
    (HTML, datetime.utcnow())
)
conn.commit()
print(f"Filas actualizadas: {cur.rowcount}")
conn.close()
print("Plantilla 32 actualizada correctamente.")
