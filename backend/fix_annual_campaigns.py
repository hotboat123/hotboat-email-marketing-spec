"""
Actualiza las 31 campañas del plan anual con el template y segmento correcto.
Ejecutar: python fix_annual_campaigns.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import Session, select, create_engine
from app.core.config import settings
from app.models.user import User          # noqa
from app.models.contact import Contact    # noqa
from app.models.segment import Segment    # noqa
from app.models.template import Template  # noqa
from app.models.campaign import Campaign
from app.models.automation import Automation, AutomationRun  # noqa
from app.models.form import SignupForm    # noqa

engine = create_engine(settings.DATABASE_URL)

# ---------------------------------------------------------------------------
# Segmentos existentes (IDs reales de tu BD)
# ---------------------------------------------------------------------------
SEG_TODOS          = 1   # Todos los suscriptores
SEG_RECURRENTES    = 2   # Clientes recurrentes
SEG_SIN_EXP        = 8   # Sin experiencia aún
SEG_SIN_ALOJ       = 9   # Sin alojamiento (solo experiencia)
SEG_VIP            = 5   # Clientes VIP
SEG_MAS3           = 11  # Más de 3 experiencias
SEG_LAPSED         = 14  # Lapsed — Sin visitar en 1 año
SEG_REACT_3_6      = 15  # Reactivación — 3 a 6 meses (≈ clientes de verano en junio)
SEG_FAMILIAS       = 22  # Familias

# ---------------------------------------------------------------------------
# Templates existentes (IDs reales de tu BD)
# ---------------------------------------------------------------------------
TMPL_NEWSLETTER     = 2   # Newsletter mensual  → emails de marca / contenido / gracias
TMPL_UPSELL_EXTRAS  = 3   # Upsell — Extras y packs especiales
TMPL_REACT          = 4   # Reactivación — Te extrañamos
TMPL_VIP_ACCESO     = 5   # VIP — Acceso anticipado a nuevas fechas
TMPL_POST_EXP       = 6   # Post-experiencia — Pide tu reseña   (pre-arrival también)
TMPL_FLASH_SALE     = 7   # Flash Sale — Oferta 48h              → urgencia / últimos cupos
TMPL_TEMPORADA_ALTA = 9   # Temporada Alta — Lanzamiento         → apertura de temporada
TMPL_BUNDLE         = 10  # Bundle — Alojamiento + Experiencia
TMPL_ENCUESTA       = 12  # Encuesta — Cuéntanos tu experiencia
TMPL_FAMILIA        = 13  # Pack Familia — Experiencia grupal     → vacaciones invierno fam.
TMPL_EARLY_BIRD     = 15  # Early Bird — Verano 2026/2027
TMPL_SAN_VAL        = 16  # San Valentín — Experiencia en pareja  → parejas
TMPL_REACT2         = 17  # Reactivación — Te echamos de menos
TMPL_OTONO          = 18  # Otoño en el agua                      → invierno/otoño editorial
TMPL_VIP_INVIERNO   = 20  # VIP — Oferta exclusiva invierno
TMPL_VAC_INVIERNO   = 21  # Vacaciones invierno — Plan familiar
TMPL_AGOSTO         = 22  # Agosto — Video gratis + Jugo natural  → agosto todos
TMPL_FIESTAS        = 23  # Fiestas Patrias — Experiencia chilena
TMPL_PRIMAVERA      = 24  # Primavera — Plan grupos de amigas     → primavera todos
TMPL_NAVIDAD        = 26  # Navidad — Felices fiestas y gift card
TMPL_REACT3         = 27  # Reactivación — Vuelve a HotBoat       → win-back 12 meses

# ---------------------------------------------------------------------------
# Mapa: nombre de campaña → (segment_id, template_id, razón)
# ---------------------------------------------------------------------------
FIXES = [
    # ── ENERO ──────────────────────────────────────────────────────────────
    (
        "[ENE] Upsell extras — clientes de temporada",
        SEG_MAS3, TMPL_UPSELL_EXTRAS,
        "Clientes 3+ visitas · Template Upsell Extras",
    ),
    (
        "[ENE] Última oportunidad — indecisos",
        SEG_SIN_EXP, TMPL_TEMPORADA_ALTA,
        "Sin experiencia aún · Template Temporada Alta (urgencia enero)",
    ),
    (
        "[ENE] Tus favoritos del verano — recurrentes",
        SEG_MAS3, TMPL_UPSELL_EXTRAS,
        "3+ visitas (tienen historial de extras) · Template Upsell Extras",
    ),
    # ── FEBRERO ────────────────────────────────────────────────────────────
    (
        "[FEB] Cierre de temporada — gracias",
        SEG_TODOS, TMPL_NEWSLETTER,
        "Todos · Template Newsletter (email de marca, sin venta)",
    ),
    (
        "[FEB] Early bird verano 26-27 — VIP",
        SEG_VIP, TMPL_EARLY_BIRD,
        "VIP · Template Early Bird Verano 2026/2027 ✓",
    ),
    # ── MARZO ──────────────────────────────────────────────────────────────
    (
        "[MAR] Lago en otoño — no han reservado",
        SEG_SIN_EXP, TMPL_OTONO,
        "Sin experiencia · Template Otoño en el agua ✓",
    ),
    (
        "[MAR] Win-back — hace tiempo que no vienen",
        SEG_LAPSED, TMPL_REACT,
        "Lapsed 1 año · Template Reactivación Te extrañamos",
    ),
    (
        "[MAR] Teaser Semana Santa — todos",
        SEG_TODOS, TMPL_NEWSLETTER,
        "Todos · Template Newsletter (teaser, aún sin precio)",
    ),
    # ── ABRIL ──────────────────────────────────────────────────────────────
    (
        "[ABR] Semana Santa — campaña principal",
        SEG_TODOS, TMPL_TEMPORADA_ALTA,
        "Todos · Template Temporada Alta (lanzamiento peak Semana Santa)",
    ),
    (
        "[ABR] Upsell alojamiento — Semana Santa",
        SEG_SIN_ALOJ, TMPL_BUNDLE,
        "Sin alojamiento · Template Bundle Alojamiento + Experiencia ✓",
    ),
    (
        "[ABR] Acceso prioritario — recurrentes",
        SEG_VIP, TMPL_VIP_ACCESO,
        "VIP · Template VIP Acceso anticipado ✓",
    ),
    # ── MAYO ───────────────────────────────────────────────────────────────
    (
        "[MAY] Behind the scenes — todos",
        SEG_TODOS, TMPL_NEWSLETTER,
        "Todos · Template Newsletter (contenido editorial, sin venta)",
    ),
    (
        "[MAY] Encuesta satisfacción — VIP",
        SEG_VIP, TMPL_ENCUESTA,
        "VIP · Template Encuesta ✓",
    ),
    # ── JUNIO ──────────────────────────────────────────────────────────────
    (
        "[JUN] Lago en invierno — editorial",
        SEG_TODOS, TMPL_OTONO,
        "Todos · Template Otoño en el agua (invierno/otoño editorial) ✓",
    ),
    (
        "[JUN] Oferta invernal — clientes solo verano",
        SEG_REACT_3_6,  # En junio, quien estuvo inactivo 3-6 meses fue en dic-feb = verano
        TMPL_VIP_INVIERNO,
        "Reactivación 3-6 meses (≈ fueron en verano) · Template VIP Oferta Invierno ✓",
    ),
    # ── JULIO ──────────────────────────────────────────────────────────────
    (
        "[JUL] Vacaciones de invierno — familias",
        SEG_FAMILIAS, TMPL_VAC_INVIERNO,
        "Familias · Template Vacaciones Invierno Plan Familiar ✓",
    ),
    (
        "[JUL] Últimos cupos vacaciones invierno — todos",
        SEG_TODOS, TMPL_FLASH_SALE,
        "Todos · Template Flash Sale (urgencia últimos cupos)",
    ),
    # ── AGOSTO ─────────────────────────────────────────────────────────────
    (
        "[AGO] Primavera se acerca — todos",
        SEG_TODOS, TMPL_AGOSTO,
        "Todos · Template Agosto (específico para agosto, anticipación primavera) ✓",
    ),
    (
        "[AGO] Win-back inactivos — hace 12 meses",
        SEG_LAPSED, TMPL_REACT3,
        "Lapsed 1 año · Template Reactivación Vuelve a HotBoat ✓",
    ),
    # ── SEPTIEMBRE ─────────────────────────────────────────────────────────
    (
        "[SEP] Acceso anticipado 18 sept — VIP",
        SEG_VIP, TMPL_VIP_ACCESO,
        "VIP · Template VIP Acceso anticipado ✓",
    ),
    (
        "[SEP] Fiestas Patrias — campaña principal",
        SEG_TODOS, TMPL_FIESTAS,
        "Todos · Template Fiestas Patrias ✓",
    ),
    (
        "[SEP] Alojamiento Fiestas Patrias — sin hospedaje",
        SEG_SIN_ALOJ, TMPL_BUNDLE,
        "Sin alojamiento · Template Bundle Alojamiento + Experiencia ✓",
    ),
    # ── OCTUBRE ────────────────────────────────────────────────────────────
    (
        "[OCT] Apertura temporada verano — anticipación",
        SEG_TODOS, TMPL_TEMPORADA_ALTA,
        "Todos · Template Temporada Alta (lanzamiento verano) ✓",
    ),
    (
        "[OCT] Pre-sale exclusivo verano — VIP",
        SEG_VIP, TMPL_EARLY_BIRD,
        "VIP · Template Early Bird (acceso anticipado exclusivo)",
    ),
    (
        "[OCT] ¿Volvés este verano? — clientes anteriores",
        SEG_RECURRENTES, TMPL_TEMPORADA_ALTA,
        "Clientes recurrentes · Template Temporada Alta",
    ),
    # ── NOVIEMBRE ──────────────────────────────────────────────────────────
    (
        "[NOV] Lanzamiento temporada alta — reservas abiertas",
        SEG_TODOS, TMPL_TEMPORADA_ALTA,
        "Todos · Template Temporada Alta — Lanzamiento ✓",
    ),
    (
        "[NOV] Urgencia cupos verano — todos",
        SEG_TODOS, TMPL_FLASH_SALE,
        "Todos · Template Flash Sale (urgencia, casi sin cupos)",
    ),
    (
        "[NOV] Bundle completo — sin alojamiento",
        SEG_SIN_ALOJ, TMPL_BUNDLE,
        "Sin alojamiento · Template Bundle Alojamiento + Experiencia ✓",
    ),
    # ── DICIEMBRE ──────────────────────────────────────────────────────────
    (
        "[DIC] Últimas fechas disponibles — indecisos",
        SEG_SIN_EXP, TMPL_FLASH_SALE,
        "Sin experiencia · Template Flash Sale (urgencia última oportunidad)",
    ),
    (
        "[DIC] Pre-arrival — reservaron diciembre",
        SEG_RECURRENTES, TMPL_POST_EXP,
        "Recurrentes (ya reservaron) · Template Post-experiencia (info pre-llegada)",
    ),
    (
        "[DIC] Felices fiestas — todos",
        SEG_TODOS, TMPL_NAVIDAD,
        "Todos · Template Navidad — Felices fiestas y gift card ✓",
    ),
]


def main():
    print("\n=== Fix: Plan Anual HotBoat — templates y segmentos ===\n")
    updated = 0
    not_found = 0

    with Session(engine) as session:
        for name, seg_id, tmpl_id, razon in FIXES:
            campaign = session.exec(
                select(Campaign).where(Campaign.name == name)
            ).first()

            if not campaign:
                print(f"  ✗ No encontrada: {name}")
                not_found += 1
                continue

            campaign.segment_id = seg_id
            campaign.template_id = tmpl_id
            session.add(campaign)
            print(f"  ✓ ID {campaign.id:3d} — {name}")
            print(f"         → seg:{seg_id}  tmpl:{tmpl_id}  ({razon})")
            updated += 1

        session.commit()

    print(f"\n  Resumen: {updated} actualizadas, {not_found} no encontradas.")
    print("\n=== Listo ===\n")


if __name__ == "__main__":
    main()
