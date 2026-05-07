"""Crea segmentos, plantillas y campañas de ejemplo para HotBoat."""
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

# ── SEGMENTOS ────────────────────────────────────────────────────────────────
SEGMENTS = [
    ("Todos los suscriptores",    "Todos los contactos con opt-in activo",
     {"operator":"AND","rules":[{"field":"opted_in","op":"eq","value":True}]}),
    ("Clientes recurrentes",      "Han hecho 2 o más experiencias HotBoat",
     {"operator":"AND","rules":[{"field":"veces_hotboat","op":"gte","value":2}]}),
    ("Primera experiencia",       "Solo han hecho 1 experiencia",
     {"operator":"AND","rules":[{"field":"veces_hotboat","op":"eq","value":1}]}),
    ("Con alojamiento",           "Han reservado alojamiento",
     {"operator":"AND","rules":[{"field":"ha_alojamiento","op":"eq","value":True}]}),
    ("Clientes VIP",              "Ticket medio >= CLP 300.000",
     {"operator":"AND","rules":[{"field":"ticket_medio","op":"gte","value":300000}]}),
    ("Llegaron por Instagram",    "Origen UTM contiene Instagram",
     {"operator":"AND","rules":[{"field":"origin_utm","op":"contains","value":"Instagram"}]}),
    ("Hablan inglés",             "Idioma en (turistas extranjeros)",
     {"operator":"AND","rules":[{"field":"language","op":"eq","value":"en"}]}),
    ("Sin experiencia aún",       "Lead que nunca ha reservado",
     {"operator":"AND","rules":[{"field":"veces_hotboat","op":"eq","value":0}]}),
]

seg_ids = []
for name, desc, cond in SEGMENTS:
    cur.execute("SELECT id FROM segments WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        seg_ids.append(row[0])
        print(f"  segmento ya existe: {name}")
    else:
        cur.execute(
            "INSERT INTO segments (name,description,conditions,created_by,created_at,updated_at) VALUES (%s,%s,%s::jsonb,%s,%s,%s) RETURNING id",
            (name, desc, json.dumps(cond), admin_id, now, now)
        )
        seg_ids.append(cur.fetchone()[0])
conn.commit()
print(f"OK {len(SEGMENTS)} segmentos")

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
        "name":    "Bienvenida — Primera reserva",
        "subject": "¡Bienvenido/a a HotBoat, {{nombre}}! 🚤",
        "preview": "Tu experiencia en el agua te espera. Aquí todo lo que necesitas saber.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#2563eb,#60a5fa);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <h1 style="color:#fff;font-size:28px;font-weight:800;margin:0 0 8px;">¡Bienvenido/a a HotBoat!</h1>
    <p style="color:rgba(255,255,255,0.9);font-size:16px;margin:0;">Nos alegra tenerte a bordo, {{nombre}}</p>
  </div>
  <p style="font-size:16px;color:#333;line-height:1.7;">Tu reserva está confirmada 🎉 Estamos listos para darte la mejor experiencia en el agua.</p>
  <div style="background:#f9fafb;border-radius:12px;padding:24px;margin:24px 0;">
    <h3 style="font-size:14px;font-weight:700;color:#111;margin:0 0 12px;text-transform:uppercase;letter-spacing:0.5px;">¿Qué incluye?</h3>
    <ul style="margin:0;padding:0 0 0 20px;color:#444;font-size:15px;line-height:2.2;">
      <li>Paseo en bote guiado</li>
      <li>Equipo de seguridad completo</li>
      <li>Fotos del recuerdo</li>
      <li>Guía experto incluido</li>
    </ul>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl" style="background:#2563eb;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Ver mi reserva</a>
  </div>
  <p style="font-size:14px;color:#666;">¿Tienes preguntas? Responde este email o escríbenos por WhatsApp.</p>
  """ + FOOTER + """
</div>""",
    },
    {
        "name":    "Newsletter mensual",
        "subject": "{{nombre}}, novedades HotBoat 🌊",
        "preview": "Nuevas fechas, experiencias y ofertas exclusivas para ti.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <h1 style="font-size:26px;font-weight:800;color:#111;margin:0 0 8px;">Hola, {{nombre}} 👋</h1>
  <p style="font-size:15px;color:#555;line-height:1.7;margin-bottom:32px;">Este mes tenemos novedades que no te puedes perder.</p>
  <div style="border-left:4px solid #2563eb;padding:16px 20px;background:#fff8f7;border-radius:0 8px 8px 0;margin-bottom:20px;">
    <h3 style="margin:0 0 6px;font-size:16px;color:#2563eb;">🗓 Nuevas fechas disponibles</h3>
    <p style="margin:0;color:#555;font-size:14px;">Reserva antes de que se agoten los cupos.</p>
  </div>
  <div style="border-left:4px solid #3b82f6;padding:16px 20px;background:#f0f7ff;border-radius:0 8px 8px 0;margin-bottom:20px;">
    <h3 style="margin:0 0 6px;font-size:16px;color:#3b82f6;">✨ Experiencia destacada</h3>
    <p style="margin:0;color:#555;font-size:14px;">Nuestra ruta al atardecer agotó cupos en 48 horas el mes pasado.</p>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl" style="background:#2563eb;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Ver todas las fechas</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name":    "Upsell — Extras y packs especiales",
        "subject": "{{nombre}}, haz tu experiencia aún más especial ❤️",
        "preview": "Añade detalles románticos y crea un momento único.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#ff6b9d,#ff8fab);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <div style="font-size:48px;margin-bottom:12px;">💑</div>
    <h1 style="color:#fff;font-size:24px;font-weight:800;margin:0 0 8px;">Haz el momento perfecto</h1>
    <p style="color:rgba(255,255,255,0.9);font-size:15px;margin:0;">Extras especiales para tu experiencia</p>
  </div>
  <p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, ¿quieres hacer tu próxima experiencia inolvidable?</p>
  <table style="width:100%;border-collapse:collapse;margin:24px 0;">
    <tr><td style="padding:16px;border:1px solid #ffe0eb;border-radius:8px;">
      <span style="font-size:24px;">🌹</span>
      <strong style="display:block;color:#111;margin-top:4px;">Pack Romántico</strong>
      <span style="color:#666;font-size:13px;">Flores, velas y champagne</span>
      <span style="display:block;font-weight:700;color:#2563eb;margin-top:4px;">+$25.000</span>
    </td></tr>
    <tr><td style="padding:4px;"></td></tr>
    <tr><td style="padding:16px;border:1px solid #e0eeff;border-radius:8px;">
      <span style="font-size:24px;">📸</span>
      <strong style="display:block;color:#111;margin-top:4px;">Sesión de Fotos</strong>
      <span style="color:#666;font-size:13px;">Fotógrafo profesional a bordo</span>
      <span style="display:block;font-weight:700;color:#2563eb;margin-top:4px;">+$35.000</span>
    </td></tr>
    <tr><td style="padding:4px;"></td></tr>
    <tr><td style="padding:16px;border:1px solid #fff0e0;border-radius:8px;">
      <span style="font-size:24px;">🎂</span>
      <strong style="display:block;color:#111;margin-top:4px;">Cumpleaños a bordo</strong>
      <span style="color:#666;font-size:13px;">Torta, decoración y sorpresa</span>
      <span style="display:block;font-weight:700;color:#2563eb;margin-top:4px;">+$20.000</span>
    </td></tr>
  </table>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl/extras" style="background:#ff6b9d;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Agregar a mi reserva</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name":    "Reactivación — Te extrañamos",
        "subject": "Ya no es lo mismo sin ti, {{nombre}} 🌊",
        "preview": "Han pasado varios meses. Vuelve a vivir la experiencia.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="text-align:center;margin-bottom:32px;">
    <div style="font-size:64px;margin-bottom:16px;">🚤</div>
    <h1 style="font-size:26px;font-weight:800;color:#111;margin:0 0 8px;">¡Te echamos de menos, {{nombre}}!</h1>
    <p style="font-size:15px;color:#666;max-width:400px;margin:0 auto;">Han pasado varios meses desde tu última experiencia. El lago te está esperando.</p>
  </div>
  <div style="background:#f9fafb;border-radius:16px;padding:28px;text-align:center;margin:24px 0;">
    <p style="font-size:15px;color:#444;margin:0 0 20px;">Como cliente especial, tenemos algo para ti:</p>
    <div style="background:#2563eb;color:#fff;border-radius:12px;padding:20px 32px;display:inline-block;">
      <div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;opacity:0.85;">Descuento exclusivo</div>
      <div style="font-size:48px;font-weight:900;line-height:1.1;">10% OFF</div>
      <div style="font-size:13px;opacity:0.85;">en tu próxima reserva</div>
    </div>
    <p style="font-size:12px;color:#999;margin-top:12px;">Válido por 15 días</p>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl" style="background:#2563eb;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Volver a reservar</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name":    "VIP — Acceso anticipado a nuevas fechas",
        "subject": "{{nombre}}, acceso exclusivo 48h antes que nadie 🌟",
        "preview": "Como cliente VIP tienes prioridad en nuevas fechas.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <div style="font-size:36px;margin-bottom:12px;">⭐</div>
    <h1 style="color:#ffd700;font-size:24px;font-weight:800;margin:0 0 8px;">Cliente VIP HotBoat</h1>
    <p style="color:rgba(255,255,255,0.8);font-size:15px;margin:0;">Acceso exclusivo 48h antes del lanzamiento público</p>
  </div>
  <p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, por tu fidelidad tienes acceso anticipado a nuestras nuevas fechas de temporada.</p>
  <div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:12px;padding:20px;margin:24px 0;">
    <p style="margin:0;font-size:14px;color:#92400e;"><strong>⏰ Solo tienes 48 horas.</strong> Después abrimos al público general y los cupos se agotan rápido.</p>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl" style="background:linear-gradient(135deg,#ffd700,#f59e0b);color:#1a1a2e;font-weight:800;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Ver mis fechas exclusivas →</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name":    "Post-experiencia — Pide tu reseña",
        "subject": "¿Cómo estuvo tu experiencia, {{nombre}}? ⭐",
        "preview": "Cuéntanos cómo te fue. Tu opinión nos ayuda a mejorar.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="text-align:center;margin-bottom:32px;">
    <div style="font-size:56px;">🌟</div>
    <h1 style="font-size:24px;font-weight:800;color:#111;margin:8px 0;">¿Cómo fue tu experiencia?</h1>
    <p style="color:#666;font-size:15px;">Esperamos que la hayas disfrutado al máximo</p>
  </div>
  <p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, tu opinión sobre la experiencia HotBoat nos ayuda a seguir mejorando.</p>
  <div style="background:#f9fafb;border-radius:12px;padding:24px;text-align:center;margin:24px 0;">
    <p style="font-size:14px;color:#666;margin:0 0 16px;">Deja tu reseña en Google Maps y ayuda a otros viajeros:</p>
    <a href="https://hotboat.cl/google-review" style="background:#4285f4;color:#fff;font-weight:600;padding:12px 28px;border-radius:8px;text-decoration:none;font-size:14px;">Escribir reseña ⭐</a>
  </div>
  <p style="font-size:14px;color:#666;text-align:center;">¿Algo que mejorar? Responde este email directamente.</p>
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
            "INSERT INTO templates (name,subject_default,preview_text,html_content,created_by,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (t["name"], t["subject"], t["preview"], t["html"], admin_id, now, now)
        )
        tpl_ids.append(cur.fetchone()[0])
conn.commit()
print(f"OK {len(TEMPLATES)} plantillas")

# ── CAMPAÑAS BORRADOR ────────────────────────────────────────────────────────
# seg_ids: [todos, recurrentes, primera, alojamiento, vip, instagram, inglés, sin_exp]
CAMPAIGNS = [
    ("Bienvenida — Primera reserva",       "¡Bienvenido/a a HotBoat, {{nombre}}! 🚤",           tpl_ids[0], seg_ids[2]),
    ("Newsletter mensual",                  "{{nombre}}, novedades HotBoat 🌊",                    tpl_ids[1], seg_ids[0]),
    ("Upsell extras — todos los clientes",  "{{nombre}}, haz tu experiencia aún más especial ❤️", tpl_ids[2], seg_ids[0]),
    ("Reactivación — clientes inactivos",   "Ya no es lo mismo sin ti, {{nombre}} 🌊",             tpl_ids[3], seg_ids[2]),
    ("VIP — Acceso anticipado fechas",      "{{nombre}}, acceso exclusivo 48h antes 🌟",           tpl_ids[4], seg_ids[4]),
    ("Post-experiencia — Pide tu reseña",   "¿Cómo estuvo tu experiencia, {{nombre}}? ⭐",         tpl_ids[5], seg_ids[0]),
]

for name, subject, tpl_id, seg_id in CAMPAIGNS:
    cur.execute("SELECT id FROM campaigns WHERE name = %s", (name,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO campaigns (name,subject,template_id,segment_id,status,created_by,created_at) VALUES (%s,%s,%s,%s,'draft',%s,%s)",
            (name, subject, tpl_id, seg_id, admin_id, now)
        )
conn.commit()
print(f"OK {len(CAMPAIGNS)} campanas borrador")
conn.close()
print("Seed completado. Recarga la app.")
