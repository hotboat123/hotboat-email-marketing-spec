"""Agrega plantillas y campanas adicionales (Klaviyo-inspired) a HotBoat."""
import os, json, psycopg2
from datetime import datetime

DB = "postgresql://postgres:mcxQvhpGaatBzcZNCbVqnGWGBjQpCNYJ@turntable.proxy.rlwy.net:48129/railway"
now = datetime.utcnow()

conn = psycopg2.connect(DB)
cur = conn.cursor()

cur.execute("SELECT id FROM users WHERE email = 'tomasdamjanic@gmail.com'")
admin_id = cur.fetchone()[0]

# ── SEGMENTOS EXTRA ──────────────────────────────────────────────────────────
NEW_SEGMENTS = [
    ("Sin alojamiento (solo experiencia)", "Han venido pero no contrataron alojamiento",
     {"operator":"AND","rules":[
         {"field":"veces_hotboat","op":"gte","value":1},
         {"field":"ha_alojamiento","op":"eq","value":False}
     ]}),
    ("Ticket alto (VIP+)", "Ticket medio >= CLP 500.000",
     {"operator":"AND","rules":[{"field":"ticket_medio","op":"gte","value":500000}]}),
    ("Mas de 3 experiencias", "Super fans con 4+ visitas",
     {"operator":"AND","rules":[{"field":"veces_hotboat","op":"gte","value":4}]}),
    ("Llegaron por Google", "Origen UTM contiene Google",
     {"operator":"AND","rules":[{"field":"origin_utm","op":"contains","value":"Google"}]}),
]

seg_ids_map = {}
for name, desc, cond in NEW_SEGMENTS:
    cur.execute("SELECT id FROM segments WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        seg_ids_map[name] = row[0]
        print(f"  segmento ya existe: {name[:40]}")
    else:
        cur.execute(
            "INSERT INTO segments (name,description,conditions,created_by,created_at,updated_at) VALUES (%s,%s,%s::jsonb,%s,%s,%s) RETURNING id",
            (name, desc, json.dumps(cond), admin_id, now, now)
        )
        seg_ids_map[name] = cur.fetchone()[0]
        print(f"  segmento creado: {name[:40]}")
conn.commit()

# Cargar todos los segmentos para referenciarlos
cur.execute("SELECT id, name FROM segments")
all_segs = {name: sid for sid, name in cur.fetchall()}

FOOTER = """
<div style="border-top:1px solid #eee;margin-top:40px;padding-top:24px;text-align:center;">
  <p style="font-size:13px;font-weight:700;color:#111;margin:0 0 4px;">HotBoat</p>
  <p style="font-size:12px;color:#999;margin:4px 0;">Experiencias en el agua &middot; Chile</p>
  <p style="font-size:12px;color:#bbb;margin:8px 0;">
    <a href="#" style="color:#bbb;">Cancelar suscripci&oacute;n</a>
  </p>
</div>"""

# ── PLANTILLAS EXTRA ─────────────────────────────────────────────────────────
NEW_TEMPLATES = [
    {
        "name": "Flash Sale — Oferta 48h",
        "subject": "{{nombre}}, solo 48h: 15% OFF en HotBoat",
        "preview": "Oferta exclusiva por tiempo limitado. Expira pronto.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:#111;border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;position:relative;overflow:hidden;">
    <div style="position:absolute;top:-20px;right:-20px;width:100px;height:100px;background:rgba(229,30,14,0.3);border-radius:50%;"></div>
    <p style="color:#e51e0e;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:2px;margin:0 0 12px;">Oferta Flash</p>
    <h1 style="color:#fff;font-size:48px;font-weight:900;margin:0;line-height:1;">15% OFF</h1>
    <p style="color:rgba(255,255,255,0.7);font-size:15px;margin:12px 0 0;">Solo por 48 horas &mdash; Vence el domingo</p>
  </div>
  <p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, como cliente especial tienes acceso anticipado a nuestra oferta flash antes que el p&uacute;blico general.</p>
  <div style="background:#fff8f7;border:2px dashed #e51e0e;border-radius:12px;padding:20px;text-align:center;margin:24px 0;">
    <p style="font-size:13px;color:#888;margin:0 0 8px;">Usa el c&oacute;digo</p>
    <p style="font-size:28px;font-weight:900;color:#e51e0e;letter-spacing:4px;margin:0;">FLASH15</p>
    <p style="font-size:12px;color:#aaa;margin:8px 0 0;">V&aacute;lido hasta el domingo 23:59</p>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl" style="background:#e51e0e;color:#fff;font-weight:700;padding:16px 40px;border-radius:10px;text-decoration:none;font-size:16px;">Reservar ahora</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name": "Referidos — Trae un amigo",
        "subject": "{{nombre}}, gana descuento trayendo un amigo",
        "preview": "Por cada amigo que reserve, tu proxima experiencia sale mas barata.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="text-align:center;margin-bottom:32px;">
    <div style="font-size:56px;margin-bottom:12px;">👥</div>
    <h1 style="font-size:26px;font-weight:800;color:#111;margin:0 0 8px;">Comparte la experiencia</h1>
    <p style="color:#666;font-size:15px;max-width:380px;margin:0 auto;">Trae un amigo a HotBoat y los dos ganan.</p>
  </div>
  <div style="display:flex;gap:16px;margin:24px 0;">
    <div style="flex:1;background:#f0f7ff;border-radius:12px;padding:20px;text-align:center;">
      <div style="font-size:28px;margin-bottom:8px;">🎁</div>
      <p style="font-weight:700;color:#111;margin:0 0 4px;font-size:14px;">T&uacute; ganas</p>
      <p style="color:#3b82f6;font-weight:800;font-size:20px;margin:0;">$10.000</p>
      <p style="color:#888;font-size:12px;margin:4px 0 0;">en tu pr&oacute;xima reserva</p>
    </div>
    <div style="flex:1;background:#f0fff4;border-radius:12px;padding:20px;text-align:center;">
      <div style="font-size:28px;margin-bottom:8px;">🤝</div>
      <p style="font-weight:700;color:#111;margin:0 0 4px;font-size:14px;">Tu amigo gana</p>
      <p style="color:#22c55e;font-weight:800;font-size:20px;margin:0;">10% OFF</p>
      <p style="color:#888;font-size:12px;margin:4px 0 0;">en su primera reserva</p>
    </div>
  </div>
  <p style="font-size:14px;color:#555;line-height:1.7;">Solo comp&aacute;rteles tu c&oacute;digo personal y cuando hagan su primera reserva, ambos ganan autom&aacute;ticamente.</p>
  <div style="background:#f9fafb;border-radius:12px;padding:20px;text-align:center;margin:24px 0;">
    <p style="font-size:13px;color:#888;margin:0 0 8px;">Tu c&oacute;digo de referido</p>
    <p style="font-size:24px;font-weight:900;color:#111;letter-spacing:3px;margin:0;">HB-{{nombre}}</p>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl/referidos" style="background:#e51e0e;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Compartir mi c&oacute;digo</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name": "Temporada Alta — Lanzamiento",
        "subject": "{{nombre}}, abrimos la temporada! Reserva antes que se llene",
        "preview": "La temporada mas esperada ya esta aqui. Cupos limitados.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#0ea5e9,#0284c7);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <div style="font-size:40px;margin-bottom:12px;">☀️🌊</div>
    <h1 style="color:#fff;font-size:28px;font-weight:800;margin:0 0 8px;">Temporada Alta 2025</h1>
    <p style="color:rgba(255,255,255,0.9);font-size:15px;margin:0;">Las fechas m&aacute;s populares ya est&aacute;n disponibles</p>
  </div>
  <p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, la temporada que todos esperan acaba de abrir. Los cupos de verano se agotan en menos de una semana.</p>
  <div style="background:#f0f9ff;border-radius:12px;padding:24px;margin:24px 0;">
    <h3 style="font-size:14px;font-weight:700;color:#0284c7;margin:0 0 16px;text-transform:uppercase;letter-spacing:0.5px;">Experiencias disponibles</h3>
    <div style="display:grid;gap:10px;">
      <div style="background:#fff;border-radius:8px;padding:12px 16px;border-left:3px solid #0ea5e9;">
        <strong style="color:#111;">🚤 Paseo cl&aacute;sico</strong> &mdash; <span style="color:#666;font-size:13px;">2 horas, hasta 8 personas</span>
      </div>
      <div style="background:#fff;border-radius:8px;padding:12px 16px;border-left:3px solid #f59e0b;">
        <strong style="color:#111;">🌅 Atardecer privado</strong> &mdash; <span style="color:#666;font-size:13px;">3 horas, pareja o familia</span>
      </div>
      <div style="background:#fff;border-radius:8px;padding:12px 16px;border-left:3px solid #22c55e;">
        <strong style="color:#111;">🏕️ Full Day + Alojamiento</strong> &mdash; <span style="color:#666;font-size:13px;">Todo incluido</span>
      </div>
    </div>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl" style="background:#0284c7;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Ver fechas disponibles</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name": "Bundle — Alojamiento + Experiencia",
        "subject": "{{nombre}}, la combinacion perfecta: bote + alojamiento",
        "preview": "Queda una noche y navega al amanecer. Paquete especial disponible.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <h1 style="font-size:26px;font-weight:800;color:#111;margin:0 0 8px;">La experiencia completa</h1>
  <p style="font-size:15px;color:#555;line-height:1.7;margin-bottom:32px;">Hola {{nombre}}, te presentamos nuestro pack m&aacute;s popular: queda una noche y navega al amanecer.</p>
  <div style="background:linear-gradient(135deg,#f9fafb,#f3f4f6);border-radius:16px;overflow:hidden;margin:24px 0;">
    <div style="background:#e51e0e;padding:16px 24px;">
      <h2 style="color:#fff;margin:0;font-size:18px;">Pack Completo HotBoat</h2>
    </div>
    <div style="padding:24px;">
      <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:16px;">
        <span style="font-size:24px;">🏠</span>
        <div>
          <strong style="color:#111;display:block;">Alojamiento en la ribera</strong>
          <span style="color:#666;font-size:13px;">Cabanitas con vista al lago, ropa de cama incluida</span>
        </div>
      </div>
      <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:16px;">
        <span style="font-size:24px;">🚤</span>
        <div>
          <strong style="color:#111;display:block;">Paseo privado en bote</strong>
          <span style="color:#666;font-size:13px;">2 horas, capitán guía, equipo de seguridad</span>
        </div>
      </div>
      <div style="display:flex;align-items:flex-start;gap:12px;">
        <span style="font-size:24px;">🍳</span>
        <div>
          <strong style="color:#111;display:block;">Desayuno incluido</strong>
          <span style="color:#666;font-size:13px;">Desayuno en terraza con vista al agua</span>
        </div>
      </div>
    </div>
    <div style="background:#fff8f7;padding:16px 24px;border-top:1px solid #fee2e2;">
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div>
          <span style="font-size:12px;color:#999;text-decoration:line-through;">Precio normal: $180.000</span>
          <div style="font-size:22px;font-weight:900;color:#e51e0e;">$149.000 <span style="font-size:14px;font-weight:400;color:#888;">/ persona</span></div>
        </div>
        <span style="background:#e51e0e;color:#fff;font-size:12px;font-weight:700;padding:4px 10px;border-radius:20px;">17% OFF</span>
      </div>
    </div>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl/pack-completo" style="background:#e51e0e;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Reservar pack completo</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name": "English — Welcome to HotBoat",
        "subject": "Welcome to HotBoat, {{nombre}}! Your adventure awaits",
        "preview": "Everything you need to know before your experience.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#0f172a,#1e3a5f);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <div style="font-size:40px;margin-bottom:12px;">⚓</div>
    <h1 style="color:#fff;font-size:28px;font-weight:800;margin:0 0 8px;">Welcome aboard, {{nombre}}!</h1>
    <p style="color:rgba(255,255,255,0.8);font-size:15px;margin:0;">Your HotBoat experience is confirmed</p>
  </div>
  <p style="font-size:15px;color:#333;line-height:1.7;">We&rsquo;re thrilled to have you with us. Here&rsquo;s everything you need to know before your adventure on the water.</p>
  <div style="background:#f8fafc;border-radius:12px;padding:24px;margin:24px 0;">
    <h3 style="font-size:14px;font-weight:700;color:#111;margin:0 0 12px;text-transform:uppercase;letter-spacing:0.5px;">What to bring</h3>
    <ul style="margin:0;padding:0 0 0 20px;color:#444;font-size:15px;line-height:2.2;">
      <li>Sunscreen and sunglasses</li>
      <li>Light clothing &amp; a warm layer</li>
      <li>Camera (we'll have memorable moments!)</li>
      <li>Valid ID</li>
    </ul>
  </div>
  <div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:12px;padding:16px 20px;margin:24px 0;">
    <p style="margin:0;font-size:14px;color:#92400e;"><strong>📍 Meeting point:</strong> HotBoat dock, 15 minutes before your scheduled time.</p>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl/en" style="background:#0284c7;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">View my booking</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name": "Encuesta — Cuetanos tu experiencia",
        "subject": "{{nombre}}, 2 minutos para mejorar HotBoat",
        "preview": "Tu opinion vale mucho. Respondenos y recibe un regalo.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="text-align:center;margin-bottom:32px;">
    <div style="font-size:56px;margin-bottom:16px;">📋</div>
    <h1 style="font-size:24px;font-weight:800;color:#111;margin:0 0 8px;">Tu opinion nos importa</h1>
    <p style="color:#666;font-size:15px;max-width:400px;margin:0 auto;">Solo 3 preguntas. Te toma 2 minutos y nos ayuda a mejorar.</p>
  </div>
  <div style="background:#f9fafb;border-radius:16px;padding:28px;margin:24px 0;">
    <div style="margin-bottom:20px;padding-bottom:20px;border-bottom:1px solid #eee;">
      <p style="font-weight:700;color:#111;margin:0 0 12px;font-size:14px;">1. &iquest;C&oacute;mo calificar&iacute;as tu experiencia?</p>
      <div style="display:flex;gap:8px;">
        <a href="#" style="width:40px;height:40px;border:2px solid #e5e7eb;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;text-decoration:none;">1</a>
        <a href="#" style="width:40px;height:40px;border:2px solid #e5e7eb;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;text-decoration:none;">2</a>
        <a href="#" style="width:40px;height:40px;border:2px solid #e5e7eb;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;text-decoration:none;">3</a>
        <a href="#" style="width:40px;height:40px;border:2px solid #e5e7eb;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;text-decoration:none;">4</a>
        <a href="#" style="width:40px;height:40px;border:2px solid #e51e0e;background:#e51e0e;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:18px;text-decoration:none;color:#fff;font-weight:700;">5</a>
      </div>
    </div>
    <p style="font-weight:700;color:#111;margin:0 0 8px;font-size:14px;">2. &iquest;Qu&eacute; fue lo mejor de tu visita?</p>
    <p style="color:#888;font-size:13px;margin:0 0 4px;">Responde a este email o haz click abajo.</p>
  </div>
  <div style="background:#fffbeb;border-radius:12px;padding:16px 20px;margin:16px 0;text-align:center;">
    <p style="font-size:13px;color:#92400e;margin:0;"><strong>Regalo:</strong> Todos los que respondan reciben un 10% de descuento en su pr&oacute;xima visita.</p>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl/encuesta" style="background:#e51e0e;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Responder encuesta (2 min)</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name": "Pack Familia — Experiencia grupal",
        "subject": "{{nombre}}, trae a toda la familia a HotBoat",
        "preview": "Paquete especial para grupos familiares. Precio por persona mas economico.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#f59e0b,#d97706);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <div style="font-size:40px;margin-bottom:12px;">👨‍👩‍👧‍👦</div>
    <h1 style="color:#fff;font-size:26px;font-weight:800;margin:0 0 8px;">Experiencia familiar HotBoat</h1>
    <p style="color:rgba(255,255,255,0.9);font-size:15px;margin:0;">Grupos de 4 a 12 personas &mdash; precio especial</p>
  </div>
  <p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, &iquest;sabias que nuestros botes tienen capacidad para familias y grupos? Tenemos el precio m&aacute;s competitivo del lago.</p>
  <div style="background:#fffbeb;border-radius:12px;padding:24px;margin:24px 0;">
    <h3 style="font-size:14px;font-weight:700;color:#92400e;margin:0 0 16px;">Incluye para todos:</h3>
    <div style="display:grid;gap:10px;">
      <div style="display:flex;gap:10px;align-items:center;">
        <span style="width:24px;height:24px;background:#f59e0b;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;">✓</span>
        <span style="color:#444;font-size:14px;">Chaleco salvavidas talla para todos</span>
      </div>
      <div style="display:flex;gap:10px;align-items:center;">
        <span style="width:24px;height:24px;background:#f59e0b;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;">✓</span>
        <span style="color:#444;font-size:14px;">Guía bilinge (espa&ntilde;ol / ingl&eacute;s)</span>
      </div>
      <div style="display:flex;gap:10px;align-items:center;">
        <span style="width:24px;height:24px;background:#f59e0b;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;">✓</span>
        <span style="color:#444;font-size:14px;">Fotos grupales del recuerdo</span>
      </div>
      <div style="display:flex;gap:10px;align-items:center;">
        <span style="width:24px;height:24px;background:#f59e0b;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;">✓</span>
        <span style="color:#444;font-size:14px;">Snacks y bebidas incluidos</span>
      </div>
    </div>
  </div>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl/grupos" style="background:#d97706;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Cotizar para mi grupo</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
    {
        "name": "Cumpleanos — Oferta especial de aniversario",
        "subject": "Feliz cumpleanos {{nombre}}! Un regalo de parte de HotBoat",
        "preview": "En tu mes especial tenemos un regalo para ti.",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="text-align:center;margin-bottom:32px;">
    <div style="font-size:64px;margin-bottom:16px;">🎂</div>
    <h1 style="font-size:28px;font-weight:800;color:#111;margin:0 0 8px;">Feliz cumplea&ntilde;os, {{nombre}}!</h1>
    <p style="color:#666;font-size:15px;">Queremos celebrar contigo</p>
  </div>
  <div style="background:linear-gradient(135deg,#fdf2f8,#fce7f3);border-radius:16px;padding:32px;text-align:center;margin:24px 0;">
    <p style="font-size:15px;color:#9d174d;margin:0 0 16px;">En tu mes especial, HotBoat te regala:</p>
    <div style="background:#fff;border-radius:12px;padding:24px;display:inline-block;min-width:200px;">
      <p style="font-size:12px;font-weight:600;color:#9d174d;text-transform:uppercase;letter-spacing:1px;margin:0 0 8px;">Tu regalo</p>
      <p style="font-size:40px;font-weight:900;color:#e51e0e;margin:0;line-height:1;">20% OFF</p>
      <p style="font-size:13px;color:#888;margin:8px 0 0;">en cualquier experiencia</p>
    </div>
    <p style="font-size:12px;color:#b45309;margin-top:16px 0 0;">V&aacute;lido durante todo tu mes de cumplea&ntilde;os.</p>
  </div>
  <p style="font-size:14px;color:#555;line-height:1.7;text-align:center;">Porque los mejores recuerdos se crean en el agua. Celébralo con nosotros.</p>
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl" style="background:#e51e0e;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Canjear mi regalo</a>
  </div>
  """ + FOOTER + """
</div>""",
    },
]

tpl_ids_map = {}
cur.execute("SELECT id, name FROM templates")
existing_templates = {name: tid for tid, name in cur.fetchall()}

for t in NEW_TEMPLATES:
    if t["name"] in existing_templates:
        tpl_ids_map[t["name"]] = existing_templates[t["name"]]
        print(f"  plantilla ya existe: {t['name'][:40]}")
    else:
        cur.execute(
            "INSERT INTO templates (name,subject_default,preview_text,html_content,created_by,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (t["name"], t["subject"], t["preview"], t["html"], admin_id, now, now)
        )
        tpl_ids_map[t["name"]] = cur.fetchone()[0]
        print(f"  plantilla creada: {t['name'][:40]}")
conn.commit()
print(f"OK plantillas")

# ── CAMPANAS EXTRA ────────────────────────────────────────────────────────────
def seg(name):
    return all_segs.get(name)

def tpl(name):
    return tpl_ids_map.get(name) or existing_templates.get(name)

NEW_CAMPAIGNS = [
    ("Flash Sale — Todos",            "Solo 48h: 15% OFF en HotBoat",
     tpl("Flash Sale — Oferta 48h"),      seg("Todos los suscriptores")),
    ("Referidos — Clientes recurrentes", "Gana descuento trayendo un amigo",
     tpl("Referidos — Trae un amigo"),    seg("Clientes recurrentes")),
    ("Temporada alta — Lista completa",  "Abrimos la temporada! Reserva antes que se llene",
     tpl("Temporada Alta — Lanzamiento"), seg("Todos los suscriptores")),
    ("Bundle alojamiento — Sin aloj",    "La combinacion perfecta: bote + alojamiento",
     tpl("Bundle — Alojamiento + Experiencia"), seg("Sin alojamiento (solo experiencia)")),
    ("Welcome — Turistas extranjeros",   "Welcome to HotBoat! Your adventure awaits",
     tpl("English — Welcome to HotBoat"), seg("Hablan ingles")),
    ("Encuesta post-experiencia",        "2 minutos para mejorar HotBoat",
     tpl("Encuesta — Cuetanos tu experiencia"), seg("Todos los suscriptores")),
    ("Pack familia — Clientes VIP",      "Trae a toda la familia a HotBoat",
     tpl("Pack Familia — Experiencia grupal"), seg("Clientes VIP")),
    ("Cumpleanos — Lista completa",      "Feliz cumpleanos! Un regalo de HotBoat",
     tpl("Cumpleanos — Oferta especial de aniversario"), seg("Todos los suscriptores")),
]

added = 0
cur.execute("SELECT name FROM campaigns")
existing_campaigns = {r[0] for r in cur.fetchall()}

for name, subject, tpl_id, seg_id in NEW_CAMPAIGNS:
    if name in existing_campaigns:
        print(f"  campana ya existe: {name[:40]}")
        continue
    if not tpl_id or not seg_id:
        print(f"  SKIP {name[:40]} (falta tpl_id={tpl_id} o seg_id={seg_id})")
        continue
    cur.execute(
        "INSERT INTO campaigns (name,subject,template_id,segment_id,status,created_by,created_at) VALUES (%s,%s,%s,%s,'draft',%s,%s)",
        (name, subject, tpl_id, seg_id, admin_id, now)
    )
    added += 1
    print(f"  campana creada: {name[:40]}")
conn.commit()
print(f"OK {added} campanas nuevas")
conn.close()
print("Seed extra completado.")
