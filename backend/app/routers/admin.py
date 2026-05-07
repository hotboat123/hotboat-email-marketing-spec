from datetime import datetime
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.database import get_session
from app.core.deps import require_admin
from app.models.user import User
from app.models.template import Template
from app.models.campaign import Campaign
from app.models.segment import Segment

router = APIRouter()

FOOTER = """
<div style="border-top:1px solid #eee;margin-top:40px;padding-top:24px;text-align:center;">
  <p style="font-size:13px;font-weight:700;color:#111;margin:0 0 4px;">HotBoat</p>
  <p style="font-size:12px;color:#999;margin:4px 0;">Experiencias en el agua &middot; Chile</p>
  <p style="font-size:12px;color:#bbb;margin:8px 0;">
    <a href="#" style="color:#bbb;">Cancelar suscripci&oacute;n</a>
  </p>
</div>"""

SEED_TEMPLATES = [
    {
        "name":    "Bienvenida — Lista HotBoat",
        "subject": "{{nombre}}, bienvenido/a a HotBoat 🌊",
        "preview": "Nos alegra tenerte aquí. Descubre lo que tenemos preparado para ti.",
        "segment": "Todos los suscriptores",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#2563eb,#60a5fa);border-radius:16px;padding:44px 40px;text-align:center;margin-bottom:32px;">
    <img src="https://hotboatchile.com/logo_hotboat.jpg" alt="HotBoat" style="height:56px;width:auto;margin-bottom:18px;display:block;margin-left:auto;margin-right:auto;" />
    <h1 style="color:#fff;font-size:28px;font-weight:800;margin:0 0 10px;line-height:1.2;">Bienvenido/a a HotBoat, {{nombre}}</h1>
    <p style="color:rgba(255,255,255,0.9);font-size:16px;margin:0;">Nos alegra tenerte en nuestra comunidad</p>
  </div>
  <p style="font-size:16px;color:#333;line-height:1.75;margin-bottom:24px;">
    Hola {{nombre}}, acabas de unirte a la lista de HotBoat.
    Desde aquí te haremos llegar las mejores experiencias en el agua,
    fechas exclusivas y ofertas especiales pensadas para ti.
  </p>
  <div style="background:#f9fafb;border-radius:14px;padding:28px;margin-bottom:28px;">
    <p style="font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;color:#999;margin:0 0 16px;">Qué recibirás</p>
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
  <div style="text-align:center;margin:32px 0;">
    <a href="https://hotboat.cl" style="background:#2563eb;color:#fff;font-weight:700;padding:15px 44px;border-radius:11px;text-decoration:none;font-size:16px;display:inline-block;">Ver experiencias disponibles</a>
  </div>
  <p style="font-size:13px;color:#aaa;text-align:center;line-height:1.6;margin-top:32px;">
    Si no quieres recibir nuestros correos, puedes darte de baja en cualquier momento desde el enlace al pie de este mensaje.
  </p>""" + FOOTER + "</div>",
    },
    {
        "name":    "Día de la Madre — Bienvenida Mamás",
        "subject": "{{nombre}}, te damos la bienvenida a HotBoat 🌊",
        "preview": "Nos alegra tenerte aquí. Descubre lo que tenemos preparado para ti.",
        "segment": "Mamás",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#2563eb,#60a5fa);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <img src="https://hotboatchile.com/logo_hotboat.jpg" alt="HotBoat" style="height:52px;width:auto;margin-bottom:16px;display:block;margin-left:auto;margin-right:auto;" />
    <h1 style="color:#fff;font-size:28px;font-weight:800;margin:0 0 8px;">¡Hola, {{nombre}}! 🌸</h1>
    <p style="color:rgba(255,255,255,0.9);font-size:16px;margin:0;">Nos alegra tenerte en la familia HotBoat</p>
  </div>
  <p style="font-size:16px;color:#333;line-height:1.7;">En HotBoat creamos experiencias únicas en el agua para que disfrutes momentos inolvidables junto a las personas que más quieres.</p>
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
    <a href="https://hotboat.cl" style="background:#2563eb;color:#fff;font-weight:700;padding:14px 36px;border-radius:10px;text-decoration:none;font-size:15px;">Conocer HotBoat</a>
  </div>
  <p style="font-size:14px;color:#666;text-align:center;">Pronto recibirás algo muy especial por el Día de la Madre. ¡Estáte atenta! 🌸</p>""" + FOOTER + "</div>",
    },
    {
        "name":    "Día de la Madre — Oferta especial",
        "subject": "{{nombre}}, tu regalo de Día de la Madre está aquí 🌸",
        "preview": "Video profesional gratis + jugo natural 1L. Solo para ti, con el cupón MAMÁ.",
        "segment": "Mamás",
        "html": """<div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px 32px;">
  <div style="background:linear-gradient(135deg,#ff6b9d,#2563eb);border-radius:16px;padding:40px;text-align:center;margin-bottom:32px;">
    <img src="https://hotboatchile.com/logo_hotboat.jpg" alt="HotBoat" style="height:52px;width:auto;margin-bottom:16px;display:block;margin-left:auto;margin-right:auto;" />
    <h1 style="color:#fff;font-size:26px;font-weight:800;margin:0 0 8px;">Feliz Día de la Madre 🌸</h1>
    <p style="color:rgba(255,255,255,0.9);font-size:16px;margin:0;">{{nombre}}, este día es tuyo. Te lo merecés todo.</p>
  </div>
  <p style="font-size:16px;color:#333;line-height:1.7;text-align:center;">Para celebrarte, preparamos un regalo especial cuando reserves tu experiencia HotBoat:</p>
  <div style="display:flex;gap:16px;margin:28px 0;flex-wrap:wrap;">
    <div style="flex:1;min-width:220px;background:#fff8f0;border:1px solid #ffd6a0;border-radius:12px;padding:20px;text-align:center;">
      <div style="font-size:40px;margin-bottom:8px;">🎬</div>
      <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 4px;">Video profesional</p>
      <p style="color:#888;font-size:13px;margin:0;">Tu experiencia filmada en HD — <strong style="color:#2563eb;">¡GRATIS!</strong></p>
    </div>
    <div style="flex:1;min-width:220px;background:#f0fff4;border:1px solid #a0f0b8;border-radius:12px;padding:20px;text-align:center;">
      <div style="font-size:40px;margin-bottom:8px;">🥤</div>
      <p style="font-weight:700;color:#111;font-size:15px;margin:0 0 4px;">Jugo natural 1 litro</p>
      <p style="color:#888;font-size:13px;margin:0;">Fresco y recién hecho — <strong style="color:#16a34a;">¡GRATIS!</strong></p>
    </div>
  </div>
  <div style="background:#f9fafb;border-radius:16px;padding:28px;text-align:center;margin:28px 0;">
    <p style="font-size:14px;color:#555;margin:0 0 12px;">Ingresa este cupón al reservar:</p>
    <div style="display:inline-block;background:#2563eb;color:#fff;border-radius:12px;padding:16px 40px;">
      <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:2px;opacity:0.85;margin-bottom:4px;">Código de reserva</div>
      <div style="font-size:42px;font-weight:900;letter-spacing:4px;line-height:1.1;">MAMÁ</div>
    </div>
    <p style="font-size:12px;color:#999;margin-top:12px;">Válido hasta el 11 de mayo de 2026</p>
  </div>
  <div style="text-align:center;margin:32px 0 16px;">
    <a href="https://whatsapp.hotboat.cl/booking" style="background:#2563eb;color:#fff;font-weight:800;padding:16px 44px;border-radius:12px;text-decoration:none;font-size:16px;display:inline-block;">Reservar ahora 🌊</a>
  </div>
  <p style="text-align:center;font-size:14px;color:#888;margin:0;">¿Quieres saber más? <a href="https://hotboat.cl" style="color:#2563eb;font-weight:600;text-decoration:none;">Ver toda la experiencia</a></p>""" + FOOTER + "</div>",
    },
]

SEED_SEGMENTS = [
    {
        "name": "Todos los suscriptores",
        "description": "Todos los contactos con opt-in activo",
        "conditions": {"operator": "AND", "rules": [{"field": "opted_in", "op": "eq", "value": True}]},
    },
    {
        "name": "Mamás",
        "description": "Contactos etiquetados como mamá (custom_fields.es_mama = true)",
        "conditions": {"operator": "AND", "rules": [
            {"field": "opted_in", "op": "eq", "value": True},
            {"field": "custom_fields.es_mama", "op": "eq", "value": "true"},
        ]},
    },
]


@router.post("/seed-templates")
def seed_templates(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Crea o actualiza plantillas y campañas de ejemplo. Solo admins. Idempotente."""
    now = datetime.utcnow()
    created = {"segments": [], "templates": [], "campaigns": []}
    updated = {"templates": []}

    # Segmentos
    seg_map: dict[str, int] = {}
    for s in SEED_SEGMENTS:
        existing = session.exec(select(Segment).where(Segment.name == s["name"])).first()
        if existing:
            seg_map[s["name"]] = existing.id
        else:
            seg = Segment(name=s["name"], description=s["description"],
                          conditions=s["conditions"], created_by=current_user.id,
                          created_at=now, updated_at=now)
            session.add(seg)
            session.flush()
            seg_map[s["name"]] = seg.id
            created["segments"].append(s["name"])

    # Plantillas y campañas
    for t in SEED_TEMPLATES:
        existing_tpl = session.exec(select(Template).where(Template.name == t["name"])).first()
        if existing_tpl:
            existing_tpl.html_content    = t["html"]
            existing_tpl.subject_default = t["subject"]
            existing_tpl.preview_text    = t["preview"]
            existing_tpl.updated_at      = now
            session.add(existing_tpl)
            tpl_id = existing_tpl.id
            updated["templates"].append(t["name"])
        else:
            tpl = Template(name=t["name"], subject_default=t["subject"], preview_text=t["preview"],
                           html_content=t["html"], created_by=current_user.id,
                           created_at=now, updated_at=now)
            session.add(tpl)
            session.flush()
            tpl_id = tpl.id
            created["templates"].append(t["name"])

        seg_id = seg_map.get(t["segment"])
        if seg_id:
            existing_camp = session.exec(select(Campaign).where(Campaign.name == t["name"])).first()
            if not existing_camp:
                camp = Campaign(name=t["name"], subject=t["subject"], template_id=tpl_id,
                                segment_id=seg_id, status="draft", created_by=current_user.id,
                                created_at=now)
                session.add(camp)
                created["campaigns"].append(t["name"])

    session.commit()
    return {"ok": True, "created": created, "updated": updated}
