"""
Calendario anual de campanas HotBoat — 12 meses, segmentos conductuales + templates.
Ejecutar: python seed_calendar.py
"""
import os, json, psycopg2
from datetime import datetime

DB = "postgresql://postgres:mcxQvhpGaatBzcZNCbVqnGWGBjQpCNYJ@turntable.proxy.rlwy.net:48129/railway"
now = datetime.utcnow()

conn = psycopg2.connect(DB)
cur = conn.cursor()

cur.execute("SELECT id FROM users WHERE email = 'tomasdamjanic@gmail.com'")
admin_id = cur.fetchone()[0]

# ── SEGMENTOS CONDUCTUALES ────────────────────────────────────────────────────
NEW_SEGMENTS = [
    (
        "Todos los suscriptores",
        "Todos los contactos con opt-in activo",
        None,  # sin filtro = todos los opted_in
    ),
    (
        "VIP — 3 o mas visitas",
        "Clientes fieles con 3 o mas experiencias",
        {"operator": "AND", "rules": [{"field": "veces_hotboat", "op": "gte", "value": 3}]},
    ),
    (
        "Lapsed — Sin visitar en 1 ano",
        "No han visitado desde antes de mayo 2025",
        {"operator": "AND", "rules": [
            {"field": "ultima_visita", "op": "lt",  "value": "2025-05-01"},
            {"field": "ultima_visita", "op": "not_null", "value": None},
        ]},
    ),
    (
        "Reactivacion — 3 a 6 meses",
        "Visitaron entre noviembre 2025 y febrero 2026",
        {"operator": "AND", "rules": [
            {"field": "ultima_visita", "op": "gte", "value": "2025-11-01"},
            {"field": "ultima_visita", "op": "lt",  "value": "2026-02-01"},
        ]},
    ),
    (
        "Primera visita reciente",
        "Solo una experiencia, visitaron en los ultimos 3 meses",
        {"operator": "AND", "rules": [
            {"field": "veces_hotboat", "op": "eq",  "value": 1},
            {"field": "ultima_visita", "op": "gte", "value": "2026-02-01"},
        ]},
    ),
    (
        "Hablan ingles",
        "Idioma configurado como ingles",
        {"operator": "AND", "rules": [{"field": "language", "op": "eq", "value": "en"}]},
    ),
    (
        "Sin visita registrada",
        "Leads que aun no han reservado (veces_hotboat = 0)",
        {"operator": "AND", "rules": [{"field": "veces_hotboat", "op": "eq", "value": 0}]},
    ),
]

cur.execute("SELECT id, name FROM segments")
existing_segs = {name: sid for sid, name in cur.fetchall()}

seg_map = dict(existing_segs)
for name, desc, cond in NEW_SEGMENTS:
    if name in existing_segs:
        print(f"  segmento ya existe: {name[:50]}")
    else:
        cur.execute(
            "INSERT INTO segments (name,description,conditions,created_by,created_at,updated_at) "
            "VALUES (%s,%s,%s::jsonb,%s,%s,%s) RETURNING id",
            (name, desc, json.dumps(cond) if cond is not None else None, admin_id, now, now),
        )
        seg_map[name] = cur.fetchone()[0]
        print(f"  segmento creado: {name[:50]}")
conn.commit()
print("OK segmentos\n")


# ── PLANTILLAS ────────────────────────────────────────────────────────────────
def card(color_top, emoji, title, body, btn_label, btn_url, btn_color="#e51e0e"):
    return f"""<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 24px;">
  <div style="background:{color_top};border-radius:16px;padding:36px;text-align:center;margin-bottom:28px;">
    <div style="font-size:44px;margin-bottom:10px;">{emoji}</div>
    <h1 style="color:#fff;font-size:26px;font-weight:800;margin:0;">{title}</h1>
  </div>
  {body}
  <div style="text-align:center;margin:32px 0;">
    <a href="{btn_url}" style="background:{btn_color};color:#fff;font-weight:700;
       padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">{btn_label}</a>
  </div>
</div>"""


TEMPLATES = [
    # ── Ene: Early Bird Verano ─────────────────────────────────────────────────
    {
        "name": "Early Bird — Verano 2026/2027",
        "subject": "{{nombre}}, reserva primero y ahorra 20% esta temporada",
        "preview": "Los cupos de verano se llenan en dias. Precio especial para ti.",
        "html": card(
            "linear-gradient(135deg,#0ea5e9,#0369a1)",
            "☀️🌊",
            "Temporada de verano abre pronto",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, como cliente anterior tienes acceso <strong>early bird</strong> antes que el p&uacute;blico general. Los cupos de diciembre y enero se agotan en menos de una semana.</p>
  <div style="background:#f0f9ff;border-radius:12px;padding:20px;margin:20px 0;">
    <p style="margin:0;font-size:14px;color:#0284c7;font-weight:700;">Beneficios de reservar ahora:</p>
    <ul style="color:#555;font-size:14px;line-height:2;margin:8px 0 0;padding-left:20px;">
      <li>20% de descuento sobre el precio regular</li>
      <li>Elecci&oacute;n preferente de horario</li>
      <li>Cancelaci&oacute;n gratuita hasta 7 d&iacute;as antes</li>
    </ul>
  </div>""",
            "Ver fechas disponibles", "https://hotboat.cl", "#0284c7",
        ),
    },
    # ── Feb: San Valentín ──────────────────────────────────────────────────────
    {
        "name": "San Valentin — Experiencia en pareja",
        "subject": "{{nombre}}, el plan perfecto para San Valentin",
        "preview": "Un paseo privado en bote al atardecer. Para dos.",
        "html": card(
            "linear-gradient(135deg,#ec4899,#be185d)",
            "💑",
            "San Valent&iacute;n en el agua",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, este 14 de febrero sorprende con algo diferente: un paseo privado al atardecer, s&oacute;lo para ustedes dos.</p>
  <div style="background:#fdf2f8;border-radius:12px;padding:20px;margin:20px 0;">
    <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:12px;">
      <span style="font-size:22px;">🌅</span>
      <div><strong style="color:#111;display:block;">Paseo privado al atardecer</strong><span style="color:#666;font-size:13px;">2 horas, bote exclusivo para dos</span></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:12px;">
      <span style="font-size:22px;">🍾</span>
      <div><strong style="color:#111;display:block;">Botella de espumante incluida</strong><span style="color:#666;font-size:13px;">Cortesia HotBoat para la ocasi&oacute;n</span></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:12px;">
      <span style="font-size:22px;">📸</span>
      <div><strong style="color:#111;display:block;">Sesion de fotos a bordo</strong><span style="color:#666;font-size:13px;">Captura el momento</span></div>
    </div>
  </div>
  <p style="font-size:13px;color:#888;text-align:center;">Cupos limitados para el 14 de febrero &mdash; Reserva antes del 10/02</p>""",
            "Reservar experiencia San Valentin", "https://hotboat.cl/san-valentin", "#be185d",
        ),
    },
    # ── Mar: Reactivación ──────────────────────────────────────────────────────
    {
        "name": "Reactivacion — Te echamos de menos",
        "subject": "{{nombre}}, hace tiempo que no te vemos en HotBoat",
        "preview": "Vuelve con un descuento especial. Te tenemos un regalo.",
        "html": card(
            "linear-gradient(135deg,#6366f1,#4338ca)",
            "👋",
            "Te echamos de menos, {{nombre}}",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Ha pasado un tiempo desde tu &uacute;ltima visita y quer&iacute;amos recordarte que el agua sigue esperando. Como gesto de bienvenida, tenemos algo especial para ti.</p>
  <div style="background:#f5f3ff;border:2px dashed #6366f1;border-radius:12px;padding:24px;text-align:center;margin:20px 0;">
    <p style="font-size:13px;color:#888;margin:0 0 8px;">Tu descuento de regreso</p>
    <p style="font-size:40px;font-weight:900;color:#4338ca;margin:0;line-height:1;">15% OFF</p>
    <p style="font-size:12px;color:#aaa;margin:8px 0 0;">C&oacute;digo: VUELVE15 &mdash; V&aacute;lido por 30 d&iacute;as</p>
  </div>
  <p style="font-size:14px;color:#555;line-height:1.7;">El lago, el sol y nuestro equipo te esperan. &iquest;Qu&eacute; d&iacute;a volvemos a verte?</p>""",
            "Volver a HotBoat", "https://hotboat.cl", "#4338ca",
        ),
    },
    # ── Abr: Otoño ────────────────────────────────────────────────────────────
    {
        "name": "Otono en el agua",
        "subject": "{{nombre}}, el otono en el lago es especial",
        "preview": "Menos gente, mismo paisaje increible. La temporada secreta.",
        "html": card(
            "linear-gradient(135deg,#f59e0b,#b45309)",
            "🍂🚤",
            "El oto&ntilde;o tiene su magia",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, mientras todos esperan el verano, los que saben reservan en oto&ntilde;o: menos turistas, el lago en calma, colores incre&iacute;bles y los mejores precios del a&ntilde;o.</p>
  <div style="background:#fffbeb;border-radius:12px;padding:20px;margin:20px 0;">
    <p style="font-weight:700;color:#92400e;margin:0 0 12px;font-size:14px;">Por qu&eacute; el oto&ntilde;o es diferente:</p>
    <div style="display:grid;gap:8px;">
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#f59e0b;font-weight:700;">→</span><span style="color:#555;font-size:14px;">Precios hasta 25% menores que en temporada alta</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#f59e0b;font-weight:700;">→</span><span style="color:#555;font-size:14px;">Reservas disponibles el mismo d&iacute;a</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#f59e0b;font-weight:700;">→</span><span style="color:#555;font-size:14px;">Atardeceres de colores &uacute;nicos en el lago</span></div>
    </div>
  </div>""",
            "Ver disponibilidad en otono", "https://hotboat.cl", "#b45309",
        ),
    },
    # ── May: Día de la madre ──────────────────────────────────────────────────
    {
        "name": "Dia de la madre — Regalo de experiencia",
        "subject": "El mejor regalo para el Dia de la Madre: HotBoat",
        "preview": "Regala una experiencia inolvidable, no una cosa mas.",
        "html": card(
            "linear-gradient(135deg,#ec4899,#f43f5e)",
            "🌸",
            "D&iacute;a de la Madre en HotBoat",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, el Dia de la Madre es el 13 de mayo. Este a&ntilde;o reg&aacute;late o regala algo que no se olvida: una tarde en el agua con quienes mas quieres.</p>
  <div style="background:#fff1f2;border-radius:12px;padding:24px;margin:20px 0;text-align:center;">
    <p style="font-size:14px;color:#9f1239;font-weight:700;margin:0 0 8px;">Gift Card HotBoat</p>
    <p style="font-size:13px;color:#555;margin:0 0 16px;">Regala el valor que quieras. La madre elige la fecha.</p>
    <div style="background:#fff;border:2px dashed #f43f5e;border-radius:8px;padding:16px;display:inline-block;">
      <p style="font-size:12px;color:#888;margin:0 0 4px;">Valor sugerido</p>
      <p style="font-size:28px;font-weight:900;color:#f43f5e;margin:0;">$60.000 CLP</p>
    </div>
  </div>
  <p style="font-size:13px;color:#888;text-align:center;">Puedes comprar la gift card online y te la enviamos por email de inmediato.</p>""",
            "Comprar gift card", "https://hotboat.cl/gift-card", "#f43f5e",
        ),
    },
    # ── Jun: VIP Invierno ─────────────────────────────────────────────────────
    {
        "name": "VIP — Oferta exclusiva invierno",
        "subject": "{{nombre}}, oferta solo para clientes VIP este invierno",
        "preview": "Por tus 3+ visitas, tienes acceso a un precio que nadie mas ve.",
        "html": card(
            "linear-gradient(135deg,#1e293b,#334155)",
            "⭐",
            "Acceso VIP — Solo para ti",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, por ser uno de nuestros clientes m&aacute;s leales (3 o m&aacute;s visitas), tienes acceso a una oferta que no publicamos en ning&uacute;n lado.</p>
  <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:24px;margin:20px 0;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
      <p style="font-weight:700;color:#111;margin:0;font-size:15px;">Pack VIP Invierno</p>
      <span style="background:#1e293b;color:#fff;font-size:11px;font-weight:700;padding:4px 10px;border-radius:20px;">EXCLUSIVO</span>
    </div>
    <div style="display:grid;gap:8px;">
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#6366f1;font-size:18px;">✓</span><span style="color:#555;font-size:14px;">2 horas en bote privado</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#6366f1;font-size:18px;">✓</span><span style="color:#555;font-size:14px;">Bebidas calientes a bordo (mate, cafe, te)</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#6366f1;font-size:18px;">✓</span><span style="color:#555;font-size:14px;">Frazadas y equipamiento de abrigo</span></div>
    </div>
    <div style="margin-top:16px;padding-top:16px;border-top:1px solid #e2e8f0;display:flex;align-items:center;justify-content:space-between;">
      <span style="font-size:13px;color:#999;text-decoration:line-through;">Precio normal: $95.000</span>
      <span style="font-size:22px;font-weight:900;color:#1e293b;">$69.000</span>
    </div>
  </div>
  <p style="font-size:13px;color:#888;text-align:center;">Disponible solo julio y agosto. Cupos limitados.</p>""",
            "Reservar mi cupo VIP", "https://hotboat.cl/vip", "#1e293b",
        ),
    },
    # ── Jul: Vacaciones invierno familias ─────────────────────────────────────
    {
        "name": "Vacaciones invierno — Plan familiar",
        "subject": "{{nombre}}, el plan de invierno perfecto para toda la familia",
        "preview": "Vacaciones de julio en el lago. Los ninos lo van a amar.",
        "html": card(
            "linear-gradient(135deg,#0891b2,#0e7490)",
            "👨‍👩‍👧‍👦🚤",
            "Vacaciones de julio en HotBoat",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, las vacaciones de invierno son ideales para el lago: sin el calor del verano, sin las multitudes. El bote es para tu familia.</p>
  <div style="background:#ecfeff;border-radius:12px;padding:20px;margin:20px 0;">
    <p style="font-weight:700;color:#0e7490;margin:0 0 12px;font-size:14px;">El plan incluye:</p>
    <div style="display:grid;gap:10px;">
      <div style="background:#fff;border-radius:8px;padding:12px 16px;border-left:3px solid #0891b2;font-size:14px;color:#333;">🚤 <strong>2 horas en bote privado</strong> para tu grupo</div>
      <div style="background:#fff;border-radius:8px;padding:12px 16px;border-left:3px solid #f59e0b;font-size:14px;color:#333;">🧃 <strong>Jugos naturales</strong> para todos</div>
      <div style="background:#fff;border-radius:8px;padding:12px 16px;border-left:3px solid #22c55e;font-size:14px;color:#333;">📹 <strong>Video del paseo</strong> para el recuerdo</div>
    </div>
  </div>
  <p style="font-size:13px;color:#888;text-align:center;">Precio especial para grupos de 4 o mas personas.</p>""",
            "Reservar para vacaciones", "https://hotboat.cl/familias", "#0e7490",
        ),
    },
    # ── Ago: Video + Jugo gratis ──────────────────────────────────────────────
    {
        "name": "Agosto — Video gratis + Jugo natural",
        "subject": "{{nombre}}, este mes: video del paseo + jugo natural GRATIS",
        "preview": "Solo en agosto. Trae el cupones y lleva tu recuerdo a casa.",
        "html": card(
            "linear-gradient(135deg,#22c55e,#15803d)",
            "🎥🥤",
            "Agosto de extras en HotBoat",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, durante agosto sumamos dos extras que no cobraremos: el video profesional de tu paseo y un jugo natural hecho en el momento.</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:20px 0;">
    <div style="background:#f0fdf4;border-radius:12px;padding:20px;text-align:center;">
      <div style="font-size:36px;margin-bottom:8px;">📹</div>
      <p style="font-weight:700;color:#15803d;margin:0 0 4px;font-size:14px;">Video del paseo</p>
      <p style="color:#888;font-size:12px;margin:0;">Editado y listo en 24h</p>
      <p style="color:#22c55e;font-weight:800;font-size:18px;margin:8px 0 0;">GRATIS</p>
    </div>
    <div style="background:#f0fdf4;border-radius:12px;padding:20px;text-align:center;">
      <div style="font-size:36px;margin-bottom:8px;">🥤</div>
      <p style="font-weight:700;color:#15803d;margin:0 0 4px;font-size:14px;">Jugo natural</p>
      <p style="color:#888;font-size:12px;margin:0;">Naranja, betarraga o mango</p>
      <p style="color:#22c55e;font-weight:800;font-size:18px;margin:8px 0 0;">GRATIS</p>
    </div>
  </div>
  <p style="font-size:13px;color:#888;text-align:center;">Sin c&oacute;digos ni condiciones. Reserva en agosto y listo.</p>""",
            "Reservar en agosto", "https://hotboat.cl", "#15803d",
        ),
    },
    # ── Sep: Fiestas Patrias ───────────────────────────────────────────────────
    {
        "name": "Fiestas Patrias — Experiencia chilena",
        "subject": "{{nombre}}, celebra Fiestas Patrias navegando",
        "preview": "18 de septiembre en el lago. Cueca, empanadas y agua.",
        "html": card(
            "linear-gradient(135deg,#dc2626,#1d4ed8)",
            "🇨🇱",
            "Fiestas Patrias en HotBoat",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, en septiembre celebramos diferente: paseo en bote, m&uacute;sica chilena de fondo, empanadas a bordo y el lago en todo su esplendor.</p>
  <div style="background:linear-gradient(135deg,#fff5f5,#eff6ff);border-radius:12px;padding:24px;margin:20px 0;border:1px solid #fecaca;">
    <p style="font-weight:700;color:#111;margin:0 0 12px;font-size:14px;text-align:center;">Pack 18 de Septiembre</p>
    <div style="display:grid;gap:8px;">
      <div style="display:flex;gap:10px;align-items:center;"><span style="font-size:18px;">🚤</span><span style="color:#555;font-size:14px;">Paseo de 2 horas en bote privado</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="font-size:18px;">🥟</span><span style="color:#555;font-size:14px;">Empanadas de pino a bordo (2 por persona)</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="font-size:18px;">🍷</span><span style="color:#555;font-size:14px;">Vino caliente o chicha de manzana</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="font-size:18px;">🎵</span><span style="color:#555;font-size:14px;">Playlist de cueca y folklore chileno</span></div>
    </div>
  </div>
  <p style="font-size:13px;color:#888;text-align:center;">Fechas: 18, 19 y 20 de septiembre. Cupos limitados.</p>""",
            "Reservar para Fiestas Patrias", "https://hotboat.cl/18-septiembre", "#dc2626",
        ),
    },
    # ── Oct: Grupos de amigas ─────────────────────────────────────────────────
    {
        "name": "Primavera — Plan grupos de amigas",
        "subject": "{{nombre}}, el plan de primavera perfecto con tus amigas",
        "preview": "Primavera en el lago. Tabla de SUP, fotos, jugos y mucha onda.",
        "html": card(
            "linear-gradient(135deg,#f472b6,#a855f7)",
            "🌸🏄‍♀️",
            "Primavera con tus amigas",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, octubre es el mes perfecto para un plan con tus amigas: el lago a temperatura ideal, florecido y con toda la energ&iacute;a de la primavera.</p>
  <div style="background:linear-gradient(135deg,#fdf2f8,#faf5ff);border-radius:12px;padding:20px;margin:20px 0;">
    <p style="font-weight:700;color:#7e22ce;margin:0 0 12px;font-size:14px;">Pack grupos (4+ personas):</p>
    <div style="display:grid;gap:8px;">
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#a855f7;font-size:18px;">✦</span><span style="color:#555;font-size:14px;">Tablas de SUP incluidas (una por persona)</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#a855f7;font-size:18px;">✦</span><span style="color:#555;font-size:14px;">Sesion de fotos grupal a bordo</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#a855f7;font-size:18px;">✦</span><span style="color:#555;font-size:14px;">Jugos naturales y snacks saludables</span></div>
      <div style="display:flex;gap:10px;align-items:center;"><span style="color:#a855f7;font-size:18px;">✦</span><span style="color:#555;font-size:14px;">Playlist a elecci&oacute;n del grupo</span></div>
    </div>
  </div>
  <p style="font-size:13px;color:#888;text-align:center;">Precio por persona se reduce con m&aacute;s integrantes.</p>""",
            "Ver plan grupos de amigas", "https://hotboat.cl/grupos", "#a855f7",
        ),
    },
    # ── Nov: Black Friday / Win-back ──────────────────────────────────────────
    {
        "name": "Black Friday — Vuelve a HotBoat",
        "subject": "{{nombre}}, Black Friday: el mejor precio del ano en HotBoat",
        "preview": "Solo el 29 de noviembre. 30% de descuento en todas las experiencias.",
        "html": card(
            "#0f172a",
            "🖤",
            "Black Friday HotBoat",
            """<p style="font-size:15px;color:#333;line-height:1.7;">Hola {{nombre}}, solo una vez al a&ntilde;o ofrecemos esto: el precio m&aacute;s bajo del a&ntilde;o en todas nuestras experiencias. Sin excepciones.</p>
  <div style="background:#111;border-radius:12px;padding:32px;text-align:center;margin:20px 0;">
    <p style="color:#888;font-size:13px;margin:0 0 4px;text-transform:uppercase;letter-spacing:2px;">Black Friday</p>
    <p style="color:#fff;font-size:60px;font-weight:900;margin:0;line-height:1;">30%</p>
    <p style="color:#888;font-size:15px;margin:4px 0 0;">en todas las experiencias</p>
    <div style="margin-top:20px;background:#fff;height:1px;"></div>
    <p style="color:#aaa;font-size:12px;margin:12px 0 0;">Solo el 29 de noviembre &mdash; 24 horas</p>
  </div>
  <div style="background:#fef9c3;border-radius:10px;padding:14px 20px;margin:16px 0;text-align:center;">
    <p style="margin:0;font-size:13px;color:#854d0e;">Usa el c&oacute;digo <strong style="font-size:16px;letter-spacing:2px;">BF30</strong> al reservar</p>
  </div>""",
            "Reservar con 30% OFF", "https://hotboat.cl/black-friday", "#e51e0e",
        ),
    },
    # ── Dic: Navidad + Gift card ───────────────────────────────────────────────
    {
        "name": "Navidad — Felices fiestas y gift card",
        "subject": "{{nombre}}, felices fiestas de parte de HotBoat",
        "preview": "Gracias por ser parte de nuestra comunidad. Un regalo para cerrar el ano.",
        "html": card(
            "linear-gradient(135deg,#166534,#15803d)",
            "🎄",
            "Felices fiestas, {{nombre}}",
            """<p style="font-size:15px;color:#333;line-height:1.7;text-align:center;">Gracias por hacer parte de este a&ntilde;o con HotBoat. Tu confianza y tu presencia en el agua son lo que nos da ener&iacute;a para seguir.</p>
  <div style="background:#f0fdf4;border-radius:16px;padding:28px;margin:24px 0;text-align:center;">
    <p style="font-size:13px;color:#166534;font-weight:600;margin:0 0 4px;text-transform:uppercase;letter-spacing:1px;">Tu regalo de navidad</p>
    <div style="background:#fff;border:2px dashed #22c55e;border-radius:10px;padding:20px;margin:12px auto;max-width:260px;">
      <p style="font-size:12px;color:#888;margin:0 0 4px;">Gift Card HotBoat</p>
      <p style="font-size:32px;font-weight:900;color:#15803d;margin:0;">$30.000</p>
      <p style="font-size:11px;color:#aaa;margin:6px 0 0;">Valido por 12 meses</p>
    </div>
    <p style="font-size:12px;color:#555;margin:12px 0 0;">Reenvia este email a alguien especial o &uacute;sala t&uacute; mismo.</p>
  </div>
  <p style="font-size:14px;color:#555;line-height:1.7;text-align:center;">Nos vemos en el lago en 2027. Feliz Navidad y pr&oacute;spero a&ntilde;o nuevo 🥂</p>""",
            "Activar gift card", "https://hotboat.cl/gift-card", "#15803d",
        ),
    },
]

# ── Insertar templates ────────────────────────────────────────────────────────
cur.execute("SELECT id, name FROM templates")
existing_tpls = {name: tid for tid, name in cur.fetchall()}
tpl_map = dict(existing_tpls)

for t in TEMPLATES:
    if t["name"] in existing_tpls:
        tpl_map[t["name"]] = existing_tpls[t["name"]]
        print(f"  plantilla ya existe: {t['name'][:50]}")
    else:
        cur.execute(
            "INSERT INTO templates (name,subject_default,preview_text,html_content,created_by,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (t["name"], t["subject"], t["preview"], t["html"], admin_id, now, now),
        )
        tpl_map[t["name"]] = cur.fetchone()[0]
        print(f"  plantilla creada: {t['name'][:50]}")
conn.commit()
print("OK plantillas\n")

# ── CAMPANAS DEL CALENDARIO ──────────────────────────────────────────────────
# (mes, nombre, asunto, plantilla, segmento)
CALENDAR = [
    ("Enero",      "Ene — Early Bird Verano 2026/27",         "Reserva primero y ahorra 20% esta temporada",
                   "Early Bird — Verano 2026/2027",            "Todos los suscriptores"),
    ("Febrero",    "Feb — San Valentin: experiencia en pareja","El plan perfecto para San Valentin",
                   "San Valentin — Experiencia en pareja",     "Todos los suscriptores"),
    ("Marzo",      "Mar — Reactivacion: vuelve a HotBoat",    "Hace tiempo que no te vemos",
                   "Reactivacion — Te echamos de menos",       "Reactivacion — 3 a 6 meses"),
    ("Abril",      "Abr — Otono en el agua",                  "El otono en el lago es especial",
                   "Otono en el agua",                         "Todos los suscriptores"),
    ("Mayo",       "May — Dia de la madre",                   "El mejor regalo para el Dia de la Madre",
                   "Dia de la madre — Regalo de experiencia",  "Todos los suscriptores"),
    ("Junio",      "Jun — Oferta VIP invierno",               "Oferta exclusiva para clientes VIP",
                   "VIP — Oferta exclusiva invierno",          "VIP — 3 o mas visitas"),
    ("Julio",      "Jul — Plan familiar vacaciones invierno", "El plan de julio para toda la familia",
                   "Vacaciones invierno — Plan familiar",      "Todos los suscriptores"),
    ("Agosto",     "Ago — Video gratis + jugo natural",       "Este mes: video + jugo gratis en cada reserva",
                   "Agosto — Video gratis + Jugo natural",     "Todos los suscriptores"),
    ("Septiembre", "Sep — Fiestas Patrias en el lago",        "Celebra el 18 navegando",
                   "Fiestas Patrias — Experiencia chilena",    "Todos los suscriptores"),
    ("Octubre",    "Oct — Primavera: plan grupos de amigas",  "Primavera en el lago con tus amigas",
                   "Primavera — Plan grupos de amigas",        "Todos los suscriptores"),
    ("Noviembre",  "Nov — Black Friday: 30% OFF",             "Solo el 29/11: el mejor precio del ano",
                   "Black Friday — Vuelve a HotBoat",          "Lapsed — Sin visitar en 1 ano"),
    ("Diciembre",  "Dic — Felices fiestas y gift card",       "Felices fiestas de parte de HotBoat",
                   "Navidad — Felices fiestas y gift card",    "Todos los suscriptores"),
]

cur.execute("SELECT name FROM campaigns")
existing_camps = {r[0] for r in cur.fetchall()}

added = 0
for mes, name, subject, tpl_name, seg_name in CALENDAR:
    if name in existing_camps:
        print(f"  campana ya existe: {name[:55]}")
        continue
    t_id = tpl_map.get(tpl_name)
    s_id = seg_map.get(seg_name)
    if not t_id or not s_id:
        print(f"  SKIP {name[:55]} (tpl={t_id}, seg={s_id})")
        continue
    cur.execute(
        "INSERT INTO campaigns (name,subject,template_id,segment_id,status,created_by,created_at) "
        "VALUES (%s,%s,%s,%s,'draft',%s,%s)",
        (name, subject, t_id, s_id, admin_id, now),
    )
    added += 1
    print(f"  [{mes}] campana creada: {name[:55]}")

conn.commit()
conn.close()
print(f"\nListo: {added} campanas nuevas creadas.")
