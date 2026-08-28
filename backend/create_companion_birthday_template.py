"""
Crea la plantilla de email para la automatizacion companion_birthday
(recordatorio de regalo de cumpleanos entre acompanantes de HotBoat).

Mismo diseno visual que la plantilla de cumpleanos propio (id 14,
"Cumpleanos - Oferta especial de aniversario"), adaptado para dirigirse al
ACOMPANANTE en vez de a quien cumple anos: sin cupon, con
{{companion_name}}/{{companion_birthday}} en vez de {{coupon_code}}.

Uso: cd backend && python create_companion_birthday_template.py
"""
import os, sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:mcxQvhpGaatBzcZNCbVqnGWGBjQpCNYJ@turntable.proxy.rlwy.net:48129/railway")
os.environ.setdefault("SECRET_KEY", "d7d21f70d39dddea51376ab9c5d7f420c19a92d9322d2eb23e72faf97466892e")
os.environ.setdefault("RESEND_API_KEY", "x")

from sqlalchemy import create_engine
from sqlmodel import Session, select
from app.models.user import User  # noqa: registra tabla users para FK
from app.models.template import Template

DB_URL = os.environ["DATABASE_URL"]
engine = create_engine(DB_URL)

with open(os.path.join(os.path.dirname(__file__), "companion_birthday_template.html"), encoding="utf-8") as f:
    HTML = f.read()

NAME = "Cumpleaños de acompañante — Sugerencia de regalo"
SUBJECT_DEFAULT = "El cumpleaños de {{companion_name}} se acerca 🎁"
PREVIEW = "Fuiste con {{companion_name}} a HotBoat — regálale otra vuelta."

with Session(engine) as session:
    existing = session.exec(select(Template).where(Template.name == NAME)).first()
    if existing:
        print(f"Ya existe la plantilla '{NAME}' (id={existing.id}) — actualizando su HTML.")
        existing.html_content = HTML
        existing.subject_default = SUBJECT_DEFAULT
        existing.preview_text = PREVIEW
        session.add(existing)
        session.commit()
        tpl_id = existing.id
    else:
        tpl = Template(
            name=NAME,
            subject_default=SUBJECT_DEFAULT,
            preview_text=PREVIEW,
            html_content=HTML,
        )
        session.add(tpl)
        session.commit()
        session.refresh(tpl)
        tpl_id = tpl.id
        print(f"Plantilla creada: id={tpl_id}")

print(f"TEMPLATE_ID={tpl_id}")
