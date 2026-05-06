"""
Inserta la plantilla de reactivacion (90+ dias sin visitar) en Railway.
Ejecutar: python seed_reactivation_template.py
"""
import sys, json, psycopg2
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = "postgresql://postgres:mcxQvhpGaatBzcZNCbVqnGWGBjQpCNYJ@turntable.proxy.rlwy.net:48129/railway"
now = datetime.utcnow()

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Te echamos de menos</title>
</head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:40px 0;">
  <tr>
    <td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header con ola -->
        <tr>
          <td style="background:linear-gradient(135deg,#0369a1 0%,#0ea5e9 60%,#38bdf8 100%);border-radius:16px 16px 0 0;padding:48px 40px 56px;text-align:center;">
            <p style="margin:0 0 8px;color:rgba(255,255,255,0.75);font-size:13px;letter-spacing:2px;text-transform:uppercase;font-weight:600;">HotBoat</p>
            <h1 style="margin:0;color:#ffffff;font-size:34px;font-weight:800;line-height:1.2;">
              ¡Te echamos de menos,<br>{{nombre}}!
            </h1>
            <p style="margin:16px 0 0;color:rgba(255,255,255,0.85);font-size:16px;line-height:1.6;">
              Ha pasado un tiempo desde tu última aventura en el agua.<br>
              Tenemos algo especial para que vuelvas.
            </p>
            <!-- ola decorativa -->
            <div style="margin-top:32px;font-size:36px;letter-spacing:4px;">🌊 🚤 🌊</div>
          </td>
        </tr>

        <!-- Mensaje principal -->
        <tr>
          <td style="background:#ffffff;padding:40px 40px 0;">
            <p style="margin:0 0 16px;color:#374151;font-size:16px;line-height:1.7;">
              Sabemos que la vida se pone ocupada, pero las mejores experiencias en el mar
              no deberían quedar en el recuerdo.
            </p>
            <p style="margin:0 0 24px;color:#374151;font-size:16px;line-height:1.7;">
              Desde tu última visita hemos añadido nuevas experiencias, mejores barcos y
              rutas exclusivas que creemos que te van a encantar.
            </p>
          </td>
        </tr>

        <!-- Experiencias destacadas -->
        <tr>
          <td style="background:#ffffff;padding:8px 40px 0;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:0 6px 0 0;" width="50%">
                  <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:12px;padding:20px;text-align:center;">
                    <div style="font-size:28px;margin-bottom:8px;">⛵</div>
                    <p style="margin:0 0 4px;color:#0369a1;font-weight:700;font-size:14px;">Paseo en velero</p>
                    <p style="margin:0;color:#64748b;font-size:13px;line-height:1.5;">Atardecer mágico con copa de vino incluida</p>
                  </div>
                </td>
                <td style="padding:0 0 0 6px;" width="50%">
                  <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:20px;text-align:center;">
                    <div style="font-size:28px;margin-bottom:8px;">🏄</div>
                    <p style="margin:0 0 4px;color:#16a34a;font-weight:700;font-size:14px;">Wakeboard &amp; Sup</p>
                    <p style="margin:0;color:#64748b;font-size:13px;line-height:1.5;">Adrenalina pura para toda la familia</p>
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Oferta especial -->
        <tr>
          <td style="background:#ffffff;padding:32px 40px 0;">
            <div style="background:linear-gradient(135deg,#fffbeb,#fef3c7);border:2px dashed #f59e0b;border-radius:16px;padding:28px;text-align:center;">
              <p style="margin:0 0 6px;color:#92400e;font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Oferta de regreso</p>
              <p style="margin:0 0 4px;color:#b45309;font-size:32px;font-weight:800;">10% OFF</p>
              <p style="margin:0 0 16px;color:#78350f;font-size:15px;">en tu próxima reserva — solo por volver</p>
              <p style="margin:0;background:#f59e0b;display:inline-block;color:#ffffff;font-size:11px;font-weight:700;letter-spacing:1.5px;padding:6px 16px;border-radius:999px;text-transform:uppercase;">
                Válido por 15 días
              </p>
            </div>
          </td>
        </tr>

        <!-- CTA -->
        <tr>
          <td style="background:#ffffff;padding:32px 40px 40px;text-align:center;">
            <a href="https://hotboat.cl/reservas"
               style="display:inline-block;background:linear-gradient(135deg,#0369a1,#0ea5e9);color:#ffffff;text-decoration:none;font-size:17px;font-weight:700;padding:16px 48px;border-radius:12px;letter-spacing:0.3px;box-shadow:0 4px 14px rgba(3,105,161,0.35);">
              Reservar mi experiencia →
            </a>
            <p style="margin:20px 0 0;color:#9ca3af;font-size:13px;">
              ¿Tienes dudas? Escríbenos a
              <a href="mailto:hola@hotboat.cl" style="color:#0ea5e9;text-decoration:none;">hola@hotboat.cl</a>
            </p>
          </td>
        </tr>

        <!-- Testimonial -->
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;padding:28px 40px;">
            <p style="margin:0 0 12px;color:#64748b;font-size:13px;font-style:italic;line-height:1.7;text-align:center;">
              "Fue la mejor experiencia del verano. Volvimos con los niños y no podíamos
              creer lo increíble que fue. ¡Ya estamos reservando para el próximo mes!"
            </p>
            <p style="margin:0;text-align:center;color:#94a3b8;font-size:12px;font-weight:600;">
              — María L., cliente HotBoat ⭐⭐⭐⭐⭐
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;border-radius:0 0 16px 16px;padding:24px 40px;text-align:center;">
            <p style="margin:0 0 4px;color:#64748b;font-size:13px;font-weight:600;">HotBoat — Experiencias en el mar</p>
            <p style="margin:0;color:#94a3b8;font-size:12px;">
              www.hotboat.cl &nbsp;|&nbsp; hola@hotboat.cl
            </p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>

</body>
</html>"""

conn = psycopg2.connect(DB)
cur = conn.cursor()

cur.execute("SELECT id FROM users WHERE email = 'tomasdamjanic@gmail.com'")
admin_id = cur.fetchone()[0]

# Verificar si ya existe
cur.execute("SELECT id FROM templates WHERE name = 'Reactivacion — Vuelve a HotBoat'")
existing = cur.fetchone()
if existing:
    print(f"Plantilla ya existe (id={existing[0]}). Actualizando HTML...")
    cur.execute(
        "UPDATE templates SET html_content=%s, updated_at=%s WHERE id=%s",
        (HTML, now, existing[0]),
    )
    tpl_id = existing[0]
else:
    cur.execute(
        "INSERT INTO templates (name, subject_default, preview_text, html_content, created_by, created_at, updated_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (
            "Reactivacion — Vuelve a HotBoat",
            "{{nombre}}, ¡te echamos de menos! Vuelve con un 10% OFF",
            "Ha pasado un tiempo desde tu última aventura. Tenemos algo especial para ti.",
            HTML,
            admin_id,
            now,
            now,
        ),
    )
    tpl_id = cur.fetchone()[0]
    print(f"Plantilla creada (id={tpl_id})")

conn.commit()
conn.close()

print(f"\nPlantilla lista: id={tpl_id}")
print("Puedes usarla en una automatizacion de tipo 'reactivacion'.")
