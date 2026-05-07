"""Crea segmento, plantillas y campañas para la campaña Día de la Madre."""
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

# ── SEGMENTO "Mamás" ─────────────────────────────────────────────────────────
# Filtra contactos donde custom_fields.es_mama == "true" (opt-in activo implícito)
SEG_NAME = "Mamás"
SEG_CONDITIONS = {
    "operator": "AND",
    "rules": [
        {"field": "opted_in",            "op": "eq",  "value": True},
        {"field": "custom_fields.es_mama", "op": "eq", "value": "true"},
    ]
}

cur.execute("SELECT id FROM segments WHERE name = %s", (SEG_NAME,))
row = cur.fetchone()
if row:
    seg_id = row[0]
    print(f"  segmento ya existe: {SEG_NAME}")
else:
    cur.execute(
        "INSERT INTO segments (name,description,conditions,created_by,created_at,updated_at) "
        "VALUES (%s,%s,%s::jsonb,%s,%s,%s) RETURNING id",
        (SEG_NAME,
         "Contactos etiquetados como mamá (custom_fields.es_mama = true)",
         json.dumps(SEG_CONDITIONS), admin_id, now, now)
    )
    seg_id = cur.fetchone()[0]
    print(f"  segmento creado: {SEG_NAME} (id={seg_id})")
conn.commit()

# ── FOOTER ───────────────────────────────────────────────────────────────────
FOOTER = """
<div style="border-top:1px solid #eee;margin-top:40px;padding-top:24px;text-align:center;">
  <p style="font-size:13px;font-weight:700;color:#111;margin:0 0 4px;">HotBoat</p>
  <p style="font-size:12px;color:#999;margin:4px 0;">Experiencias en el agua &middot; Chile</p>
  <p style="font-size:12px;color:#bbb;margin:8px 0;">
    <a href="#" style="color:#bbb;">Cancelar suscripci&oacute;n</a>
  </p>
</div>"""

# ── PLANTILLAS ───────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "name":    "Día de la Madre — Bienvenida Mamás",
        "subject": "{{nombre}}, te damos la bienvenida a HotBoat 🌊",
        "preview": "Nos alegra tenerte aquí. Descubre lo que tenemos preparado para ti.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#e51e0e,#ff6b5b);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <div style="font-size:48px;margin-bottom:12px;">🌸</div>
    <h1 style="color:#fff;font-size:28px;font-weight:800;margin:0 0 8px;">¡Hola, {{nombre}}!</h1>
    <p style="color:rgba(255,255,255,0.9);font-size:16px;margin:0;">Nos alegra tenerte en la familia HotBoat</p>
  </div>

  <p style="font-size:16px;color:#333;line-height:1.7;">
    En HotBoat creamos experiencias únicas en el agua para que disfrutes momentos inolvidables
    junto a las personas que más quieres.
  </p>

  <div style="background:#f9fafb;border-radius:12px;padding:24px;margin:24px 0;">
    <h3 style="font-size:14px;font-weight:700;color:#111;margin:0 0 14px;text-transform:uppercase;letter-spacing:0.5px;">¿Qué encontrarás en HotBoat?</h3>
    <ul style="margin:0;padding:0 0 0 20px;color:#444;font-size:15px;line-height:2.2;">
      <li>Paseos en bote guiados por expertos</li>
      <li>Experiencias a medida para cada ocasión</li>
      <li>Fotos y recuerdos para llevar siempre</li>
      <li>El lago más hermoso de Chile</li>
    </ul>
  </div>

  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl"
       style="background:#e51e0e;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">
      Conocer HotBoat
    </a>
  </div>

  <p style="font-size:14px;color:#666;text-align:center;">
    Pronto recibirás algo muy especial por el Día de la Madre. ¡Estáte atenta! 🌸
  </p>
""" + FOOTER + """
</div>""",
    },
    {
        "name":    "Día de la Madre — Oferta especial",
        "subject": "{{nombre}}, tu regalo de Día de la Madre está aquí 🌸",
        "preview": "Video profesional gratis + jugo natural 1L. Solo para ti, con el cupón MAMÁ.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">

  <!-- Header festivo -->
  <div style="background:linear-gradient(135deg,#ff6b9d,#e51e0e);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <div style="font-size:52px;margin-bottom:12px;">🌸</div>
    <h1 style="color:#fff;font-size:26px;font-weight:800;margin:0 0 8px;">Feliz Día de la Madre</h1>
    <p style="color:rgba(255,255,255,0.9);font-size:16px;margin:0;">
      {{nombre}}, este día es tuyo. Te lo merecés todo.
    </p>
  </div>

  <p style="font-size:16px;color:#333;line-height:1.7;text-align:center;">
    Para celebrarte, preparamos un regalo especial cuando reserves tu experiencia HotBoat:
  </p>

  <!-- Regalos -->
  <div style="display:flex;gap:16px;margin:28px 0;flex-wrap:wrap;">
    <div style="flex:1;min-width:220px;background:#fff8f0;border:1px solid #ffd6a0;border-radius:12px;padding:20px;text-align:center;">
      <div style="font-size:40px;margin-bottom:8px;">🎬</div>
      <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 4px;">Video profesional</p>
      <p style="color:#888;font-size:13px;margin:0;">Tu experiencia filmada en HD — <strong style="color:#e51e0e;">¡GRATIS!</strong></p>
    </div>
    <div style="flex:1;min-width:220px;background:#f0fff4;border:1px solid #a0f0b8;border-radius:12px;padding:20px;text-align:center;">
      <div style="font-size:40px;margin-bottom:8px;">🥤</div>
      <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 4px;">Jugo natural 1 litro</p>
      <p style="color:#888;font-size:13px;margin:0;">Fresco y recién hecho — <strong style="color:#16a34a;">¡GRATIS!</strong></p>
    </div>
  </div>

  <!-- Cupón -->
  <div style="background:#f9fafb;border-radius:16px;padding:28px;text-align:center;margin:28px 0;">
    <p style="font-size:14px;color:#555;margin:0 0 12px;">Ingresa este cupón al reservar:</p>
    <div style="display:inline-block;background:#e51e0e;color:#fff;border-radius:12px;padding:16px 40px;">
      <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:2px;opacity:0.85;margin-bottom:4px;">Código de reserva</div>
      <div style="font-size:42px;font-weight:900;letter-spacing:4px;line-height:1.1;">MAMÁ</div>
    </div>
    <p style="font-size:12px;color:#999;margin-top:12px;">Válido hasta el 11 de mayo de 2026</p>
  </div>

  <!-- CTA principal -->
  <div style="text-align:center;margin:32px 0 16px;">
    <a href="https://whatsapp.hotboat.cl/booking"
       style="background:#e51e0e;color:#fff;font-weight:800;padding:16px 44px;border-radius:12px;text-decoration:none;font-size:16px;display:inline-block;">
      Reservar ahora 🌊
    </a>
  </div>

  <!-- Link secundario -->
  <p style="text-align:center;font-size:14px;color:#888;margin:0;">
    ¿Quieres saber más antes de reservar?
    <a href="https://hotboat.cl" style="color:#e51e0e;font-weight:600;text-decoration:none;">Ver toda la experiencia</a>
  </p>

""" + FOOTER + """
</div>""",
    },
]

tpl_ids = []
for t in TEMPLATES:
    cur.execute("SELECT id FROM templates WHERE name = %s", (t["name"],))
    row = cur.fetchone()
    if row:
        tpl_ids.append(row[0])
        print(f"  plantilla ya existe: {t['name']}")
    else:
        cur.execute(
            "INSERT INTO templates (name,subject_default,preview_text,html_content,created_by,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (t["name"], t["subject"], t["preview"], t["html"], admin_id, now, now)
        )
        tpl_ids.append(cur.fetchone()[0])
        print(f"  plantilla creada: {t['name']}")
conn.commit()
print(f"OK {len(TEMPLATES)} plantillas")

# ── CAMPAÑAS ─────────────────────────────────────────────────────────────────
CAMPAIGNS = [
    (
        "Día de la Madre — Bienvenida Mamás",
        "{{nombre}}, te damos la bienvenida a HotBoat 🌊",
        tpl_ids[0],
        seg_id,
    ),
    (
        "Día de la Madre — Oferta especial (video + jugo)",
        "{{nombre}}, tu regalo de Día de la Madre está aquí 🌸",
        tpl_ids[1],
        seg_id,
    ),
]

for name, subject, tpl_id, seg in CAMPAIGNS:
    cur.execute("SELECT id FROM campaigns WHERE name = %s", (name,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO campaigns (name,subject,template_id,segment_id,status,created_by,created_at) "
            "VALUES (%s,%s,%s,%s,'draft',%s,%s)",
            (name, subject, tpl_id, seg, admin_id, now)
        )
        print(f"  campaña creada: {name}")
    else:
        print(f"  campaña ya existe: {name}")
conn.commit()

conn.close()
print("\nSeed Día de la Madre completado.")
print("Pasos siguientes:")
print("  1. Etiqueta a las contactos mamás: UPDATE contacts SET custom_fields = jsonb_set(COALESCE(custom_fields,'{}'), '{es_mama}', 'true') WHERE email IN (...);")
print("  2. Revisa las campañas en borrador y envíalas desde la app.")
