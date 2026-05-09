"""Crea la plantilla de disculpas, el segmento de afectados y la campaña borrador."""
import os, json, psycopg2
from datetime import datetime

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:mcxQvhpGaatBzcZNCbVqnGWGBjQpCNYJ@turntable.proxy.rlwy.net:48129/railway")
os.environ.setdefault("SECRET_KEY",   "d7d21f70d39dddea51376ab9c5d7f420c19a92d9322d2eb23e72faf97466892e")
os.environ.setdefault("RESEND_API_KEY","re_YRCU8htG_LzMTcMFuLx3ccxkF83nXK4b2")

DB  = os.environ["DATABASE_URL"]
now = datetime.utcnow()

conn = psycopg2.connect(DB)
cur  = conn.cursor()

cur.execute("SELECT id FROM users WHERE email = 'tomasdamjanic@gmail.com'")
admin_id = cur.fetchone()[0]

# ── PLANTILLA ────────────────────────────────────────────────────────────────
TPL_NAME = "Disculpas — Error de sistema"
TPL_HTML = """<div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;padding:40px 24px;color:#222;">

  <!-- Logo pequeño y discreto -->
  <div style="margin-bottom:32px;">
    <img src="https://hotboatchile.com/logo_hotboat_blanco.png" alt="HotBoat"
         style="height:36px;width:auto;filter:brightness(0);opacity:0.5;" />
  </div>

  <!-- Cuerpo -->
  <p style="font-size:16px;line-height:1.75;margin:0 0 16px;">
    Hola {{nombre}},
  </p>

  <p style="font-size:16px;line-height:1.75;margin:0 0 16px;">
    Hace un rato te llegó un correo mío que decía
    <em>"¡Bienvenido/a a HotBoat! Tu reserva está confirmada 🎉"</em>
  </p>

  <p style="font-size:16px;line-height:1.75;margin:0 0 16px;">
    <strong>Fue un error mío, no una estafa ni un cobro.</strong>
  </p>

  <p style="font-size:16px;line-height:1.75;margin:0 0 16px;">
    Lo que pasó es que estoy construyendo por primera vez el sistema de
    comunicaciones de HotBoat, y al cargar una lista de clientes, se disparó
    automáticamente un mail con la plantilla equivocada.
  </p>

  <p style="font-size:16px;line-height:1.75;margin:0 0 24px;">
    No volverá a pasar&nbsp;:).&nbsp; Igualmente puedes desuscribirte de los
    mails en la parte de abajo.
  </p>

  <p style="font-size:16px;line-height:1.75;margin:0 0 8px;">
    Perdón de verdad.
  </p>

  <p style="font-size:16px;line-height:1.75;margin:0 0 4px;">
    Un abrazo,
  </p>
  <p style="font-size:16px;font-weight:700;margin:0 0 4px;">Tomás</p>
  <p style="font-size:14px;color:#888;margin:0;">HotBoat&nbsp;🌊</p>

  <!-- Footer con unsub -->
  <div style="margin-top:40px;padding-top:20px;border-top:1px solid #e5e7eb;
              text-align:center;font-size:12px;color:#9ca3af;
              font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
    Recibiste este correo porque eres cliente de <strong style="color:#6b7280">HotBoat</strong>.
    &nbsp;&middot;&nbsp;
    <a href="##unsub##" style="color:#9ca3af;text-decoration:underline;">Cancelar suscripción</a>
  </div>

</div>"""

cur.execute("SELECT id FROM templates WHERE name = %s", (TPL_NAME,))
row = cur.fetchone()
if row:
    tpl_id = row[0]
    cur.execute("UPDATE templates SET html_content=%s, updated_at=%s WHERE id=%s",
                (TPL_HTML, now, tpl_id))
    print(f"  plantilla actualizada: {TPL_NAME} (id={tpl_id})")
else:
    cur.execute(
        "INSERT INTO templates (name,subject_default,preview_text,html_content,created_by,created_at,updated_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (TPL_NAME,
         "Disculpas de Tomás de HotBoat",
         "Fue un error mío — no una estafa ni un cobro.",
         TPL_HTML, admin_id, now, now)
    )
    tpl_id = cur.fetchone()[0]
    print(f"  plantilla creada: {TPL_NAME} (id={tpl_id})")
conn.commit()

# ── SEGMENTO — contactos del T&C import ─────────────────────────────────────
SEG_NAME = "Afectados — Error bienvenida T&C"
seg_conditions = {
    "operator": "AND",
    "rules": [
        {"field": "origin_utm", "op": "eq", "value": "Formulario T&C"},
        {"field": "opted_in",   "op": "eq", "value": True},
    ]
}
cur.execute("SELECT id FROM segments WHERE name = %s", (SEG_NAME,))
row = cur.fetchone()
if row:
    seg_id = row[0]
    print(f"  segmento ya existe: {SEG_NAME} (id={seg_id})")
else:
    cur.execute(
        "INSERT INTO segments (name,description,conditions,created_by,created_at,updated_at) "
        "VALUES (%s,%s,%s::jsonb,%s,%s,%s) RETURNING id",
        (SEG_NAME,
         "Contactos importados del formulario T&C que recibieron el mail equivocado",
         json.dumps(seg_conditions),
         admin_id, now, now)
    )
    seg_id = cur.fetchone()[0]
    print(f"  segmento creado: {SEG_NAME} (id={seg_id})")
conn.commit()

# ── CAMPAÑA BORRADOR ─────────────────────────────────────────────────────────
CAM_NAME = "Disculpas — Error bienvenida T&C"
cur.execute("SELECT id FROM campaigns WHERE name = %s", (CAM_NAME,))
if not cur.fetchone():
    cur.execute(
        "INSERT INTO campaigns (name,subject,template_id,segment_id,status,created_by,created_at) "
        "VALUES (%s,%s,%s,%s,'draft',%s,%s)",
        (CAM_NAME,
         "Disculpas de Tomás de HotBoat",
         tpl_id, seg_id, admin_id, now)
    )
    print(f"  campaña creada: {CAM_NAME}")
else:
    print(f"  campaña ya existe: {CAM_NAME}")
conn.commit()

# ── RESUMEN ──────────────────────────────────────────────────────────────────
cur.execute("""
    SELECT COUNT(*) FROM contacts
    WHERE origin_utm = 'Formulario T&C' AND opted_in = true
""")
total = cur.fetchone()[0]
print(f"\n  Contactos afectados en el segmento: {total}")

conn.close()
print("\nListo. Ve a Campañas y envía 'Disculpas — Error bienvenida T&C'.")
