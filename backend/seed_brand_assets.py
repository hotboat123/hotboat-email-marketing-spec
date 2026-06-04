"""
Crea la tabla brand_assets y la pobla con los assets de marca de HotBoat.
Ejecutar: python seed_brand_assets.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import Session, select, create_engine, SQLModel
from app.core.config import settings
from app.models.user import User; from app.models.contact import Contact
from app.models.segment import Segment; from app.models.template import Template
from app.models.campaign import Campaign
from app.models.automation import Automation, AutomationRun
from app.models.form import SignupForm
from app.models.brand_asset import BrandAsset

engine = create_engine(settings.DATABASE_URL)
SQLModel.metadata.create_all(engine)  # crea la tabla si no existe

ASSETS = [
    # ── COLORES ─────────────────────────────────────────────────────────────
    ("color", "Azul principal",    "#2563eb", "CTA buttons, links y acentos principales. Base de la identidad."),
    ("color", "Azul oscuro",       "#1d4ed8", "Hover de botones azules. Versión más profunda del azul principal."),
    ("color", "Navy profundo",     "#0d1b2a", "Fondos de headers oscuros. Evoca el lago de noche."),
    ("color", "Cyan eléctrico",    "#00c8ff", "Acento cyber / verano. Usar con moderación sobre fondos oscuros."),
    ("color", "Dorado",            "#f59e0b", "CTA premium, campañas de lujo, elementos de acento cálido."),
    ("color", "Naranja energía",   "#f97316", "Emails de urgencia, campañas de descuento, brutalismo."),
    ("color", "Verde éxito",       "#22c55e", "Labels GRATIS, confirmaciones, highlights positivos."),
    ("color", "Blanco",            "#ffffff", "Fondos de emails, texto sobre oscuros."),
    ("color", "Gris texto",        "#4a5568", "Cuerpo de texto principal en emails claros."),
    ("color", "Gris suave",        "#f7fafc", "Fondos de secciones, alternativas al blanco puro."),
    ("color", "Gris borde",        "#e2e8f0", "Separadores, bordes sutiles."),

    # ── TIPOGRAFÍA ───────────────────────────────────────────────────────────
    ("tipografia", "Fuente principal",       "Inter",        "Font base de todos los emails. Importar desde Google Fonts."),
    ("tipografia", "Fuente títulos grandes", "Inter 800-900","Tamaño 26-38px. Peso extrabold o black para headlines."),
    ("tipografia", "Fuente subtítulos",      "Inter 600-700","Tamaño 18-22px. Semibold o bold."),
    ("tipografia", "Fuente cuerpo",          "Inter 400",    "Tamaño 14-16px. Regular. Line-height 1.6-1.7."),
    ("tipografia", "Fuente labels/caps",     "Inter 600-700","Tamaño 10-12px. Uppercase. Letter-spacing 2-3px."),
    ("tipografia", "Fuente cupones",         "monospace 700","Para códigos de descuento. Letter-spacing 4-6px."),
    ("tipografia", "Import Google Fonts",    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap",
                                             "Línea a incluir en el <head> de todos los emails."),

    # ── LOGOS ────────────────────────────────────────────────────────────────
    ("logo", "Logo blanco (con fondo)",      "https://hotboatchile.com/logo_hotboat_blanco.png",
             "Logo blanco. Usar sobre fondos oscuros (navy, negro). Altura recomendada: 60-80px en email."),
    ("logo", "Logo invertido (oscuro)",      "https://hotboatchile.com/logo_hotboat_blanco.png",
             "Aplicar filter CSS: invert(1) sepia(1) saturate(2) brightness(0.25) para usar sobre fondos claros."),

    # ── URLS DE MARCA ────────────────────────────────────────────────────────
    ("url", "Reservas (WhatsApp)",  "https://whatsapp.hotboat.cl/booking", "Link principal de CTA en todos los emails."),
    ("url", "Sitio web",            "https://hotboat.cl",                  "Footer y links secundarios."),
    ("url", "Email remitente",      "hola@hotboat.cl",                     "From address en Resend."),

    # ── ESPACIADO ────────────────────────────────────────────────────────────
    ("espaciado", "Ancho máximo email",    "600px",   "Max-width del contenedor principal de todos los emails."),
    ("espaciado", "Padding lateral",       "40-48px", "Padding interno horizontal del email en desktop."),
    ("espaciado", "Padding sección",       "32-40px", "Espacio vertical entre secciones principales."),
    ("espaciado", "Border-radius cards",   "12-16px", "Redondeo estándar de tarjetas y bloques."),
    ("espaciado", "Border-radius botones", "8-12px",  "Redondeo estándar de botones CTA."),
]


def main():
    print("\n=== Seed: Plantillas de la Marca HotBoat ===\n")
    created = 0
    skipped = 0

    with Session(engine) as session:
        for categoria, nombre, valor, descripcion in ASSETS:
            existing = session.exec(
                select(BrandAsset).where(
                    BrandAsset.categoria == categoria,
                    BrandAsset.nombre == nombre,
                )
            ).first()

            if existing:
                existing.valor = valor
                existing.descripcion = descripcion
                session.add(existing)
                skipped += 1
            else:
                asset = BrandAsset(
                    categoria=categoria,
                    nombre=nombre,
                    valor=valor,
                    descripcion=descripcion,
                )
                session.add(asset)
                print(f"  + [{categoria:12s}] {nombre}")
                created += 1

        session.commit()

    print(f"\n  Resumen: {created} creados, {skipped} actualizados.")
    print("\n=== Listo ===\n")


if __name__ == "__main__":
    main()
