"""Crea la plantilla y campaña de Bienvenida a la lista HotBoat."""
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

# Segmento "Todos los suscriptores" (ya existe, lo reutilizamos)
cur.execute("SELECT id FROM segments WHERE name = 'Todos los suscriptores'")
row = cur.fetchone()
if not row:
    cur.execute(
        "INSERT INTO segments (name,description,conditions,created_by,created_at,updated_at) "
        "VALUES (%s,%s,%s::jsonb,%s,%s,%s) RETURNING id",
        ("Todos los suscriptores", "Todos los contactos con opt-in activo",
         json.dumps({"operator":"AND","rules":[{"field":"opted_in","op":"eq","value":True}]}),
         admin_id, now, now)
    )
    row = (cur.fetchone()[0],)
seg_id = row[0]
conn.commit()
print(f"  segmento id={seg_id}")

# ── PLANTILLA ────────────────────────────────────────────────────────────────
TPL_NAME = "Bienvenida — Lista HotBoat"
TPL_HTML = """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#2563eb,#60a5fa);border-radius:16px;padding:44px 40px;text-align:center;margin-bottom:32px;">
    <img src="https://hotboatchile.com/logo_hotboat.jpg" alt="HotBoat" style="height:56px;width:auto;margin-bottom:18px;display:block;margin-left:auto;margin-right:auto;" />
    <h1 style="color:#fff;font-size:28px;font-weight:800;margin:0 0 10px;line-height:1.2;">
      Bienvenido/a a HotBoat, {{nombre}}
    </h1>
    <p style="color:rgba(255,255,255,0.9);font-size:16px;margin:0;">
      Nos alegra tenerte en nuestra comunidad
    </p>
  </div>

  <!-- Intro -->
  <p style="font-size:16px;color:#333;line-height:1.75;margin-bottom:24px;">
    Hola {{nombre}}, acabas de unirte a la lista de HotBoat.
    Desde aquí te haremos llegar las mejores experiencias en el agua,
    fechas exclusivas y ofertas especiales pensadas para ti.
  </p>

  <!-- Qué recibirás -->
  <div style="background:#f9fafb;border-radius:14px;padding:28px;margin-bottom:28px;">
    <p style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#999;margin:0 0 16px;">
      Qué recibirás
    </p>
    <div style="display:flex;flex-direction:column;gap:12px;">
      <div style="display:flex;align-items:flex-start;gap:14px;">
        <span style="font-size:22px;line-height:1;flex-shrink:0;">📅</span>
        <div>
          <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 2px;">Nuevas fechas antes que nadie</p>
          <p style="color:#666;font-size:14px;margin:0;">Acceso anticipado cuando abramos nuevos cupos.</p>
        </div>
      </div>
      <div style="display:flex;align-items:flex-start;gap:14px;">
        <span style="font-size:22px;line-height:1;flex-shrink:0;">🎁</span>
        <div>
          <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 2px;">Ofertas y beneficios exclusivos</p>
          <p style="color:#666;font-size:14px;margin:0;">Descuentos y experiencias solo para nuestra lista.</p>
        </div>
      </div>
      <div style="display:flex;align-items:flex-start;gap:14px;">
        <span style="font-size:22px;line-height:1;flex-shrink:0;">🌊</span>
        <div>
          <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 2px;">Contenido del lago y el agua</p>
          <p style="color:#666;font-size:14px;margin:0;">Tips, historias y momentos de la comunidad HotBoat.</p>
        </div>
      </div>
    </div>
  </div>

  <!-- CTA -->
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl"
       style="background:#2563eb;color:#fff;font-weight:700;padding:15px 44px;border-radius:11px;text-decoration:none;font-size:16px;display:inline-block;">
      Ver experiencias disponibles
    </a>
  </div>

  <!-- Nota desuscripción -->
  <p style="font-size:13px;color:#aaa;text-align:center;line-height:1.6;margin-top:32px;">
    Si no quieres recibir nuestros correos, puedes
    darte de baja en cualquier momento desde el enlace
    al pie de este mensaje. Sin preguntas.
  </p>

  <!-- Footer decorativo -->
  <div style="border-top:1px solid #eee;margin-top:36px;padding-top:24px;text-align:center;">
    <p style="font-size:13px;font-weight:700;color:#111;margin:0 0 4px;">HotBoat</p>
    <p style="font-size:12px;color:#999;margin:4px 0;">Experiencias en el agua &middot; Chile</p>
  </div>

</div>"""

cur.execute("SELECT id FROM templates WHERE name = %s", (TPL_NAME,))
row = cur.fetchone()
if row:
    tpl_id = row[0]
    print(f"  plantilla ya existe: {TPL_NAME} (id={tpl_id})")
else:
    cur.execute(
        "INSERT INTO templates (name,subject_default,preview_text,html_content,created_by,created_at,updated_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (TPL_NAME,
         "{{nombre}}, bienvenido/a a HotBoat 🌊",
         "Nos alegra tenerte aquí. Descubre lo que tenemos preparado para ti.",
         TPL_HTML, admin_id, now, now)
    )
    tpl_id = cur.fetchone()[0]
    print(f"  plantilla creada: {TPL_NAME} (id={tpl_id})")
conn.commit()

# ── CAMPAÑA BORRADOR ─────────────────────────────────────────────────────────
CAM_NAME = "Bienvenida — Lista HotBoat"
cur.execute("SELECT id FROM campaigns WHERE name = %s", (CAM_NAME,))
if not cur.fetchone():
    cur.execute(
        "INSERT INTO campaigns (name,subject,template_id,segment_id,status,created_by,created_at) "
        "VALUES (%s,%s,%s,%s,'draft',%s,%s)",
        (CAM_NAME,
         "{{nombre}}, bienvenido/a a HotBoat 🌊",
         tpl_id, seg_id, admin_id, now)
    )
    print(f"  campaña creada: {CAM_NAME}")
else:
    print(f"  campaña ya existe: {CAM_NAME}")
conn.commit()

conn.close()
print("\nSeed bienvenida completado.")
print("La campaña está en borrador — envía primero a 20 contactos para validar aperturas y clics.")
