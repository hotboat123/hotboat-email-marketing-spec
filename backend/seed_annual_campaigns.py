"""
Seed: Plan Anual de Email Marketing HotBoat 2026
Crea segmentos y 31 campañas draft (una por email del plan anual).
Ejecutar: python seed_annual_campaigns.py
Las campañas quedan en estado 'draft' — asignar template correcto y scheduled_at antes de activar.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import Session, select, create_engine
from app.core.config import settings

# Importar TODOS los modelos para que SQLAlchemy resuelva los FK entre tablas
from app.models.user import User  # noqa: F401
from app.models.contact import Contact  # noqa: F401
from app.models.segment import Segment
from app.models.template import Template
from app.models.campaign import Campaign
from app.models.automation import Automation, AutomationRun  # noqa: F401
from app.models.form import SignupForm  # noqa: F401

engine = create_engine(settings.DATABASE_URL)

# ---------------------------------------------------------------------------
# Segmentos del plan anual
# ---------------------------------------------------------------------------
SEGMENTS = [
    {
        "name": "[Plan Anual] Todos los suscriptores",
        "description": "Contactos con opted_in activo. Base general para campañas masivas.",
        "conditions": {
            "operator": "AND",
            "rules": [{"field": "opted_in", "op": "eq", "value": True}],
        },
    },
    {
        "name": "[Plan Anual] Clientes recurrentes (3+ visitas)",
        "description": "Han ido a HotBoat 3 o más veces. Alta fidelidad y afinidad con la marca.",
        "conditions": {
            "operator": "AND",
            "rules": [
                {"field": "opted_in", "op": "eq", "value": True},
                {"field": "veces_hotboat", "op": "gte", "value": 3},
            ],
        },
    },
    {
        "name": "[Plan Anual] Clientes VIP (5+ visitas)",
        "description": "Han ido 5 o más veces. Máxima fidelidad — acceso anticipado y beneficios exclusivos.",
        "conditions": {
            "operator": "AND",
            "rules": [
                {"field": "opted_in", "op": "eq", "value": True},
                {"field": "veces_hotboat", "op": "gte", "value": 5},
            ],
        },
    },
    {
        "name": "[Plan Anual] Sin alojamiento",
        "description": "Nunca han reservado alojamiento. Objetivo: upsell de hospedaje.",
        "conditions": {
            "operator": "AND",
            "rules": [
                {"field": "opted_in", "op": "eq", "value": True},
                {"field": "ha_alojamiento", "op": "eq", "value": False},
            ],
        },
    },
    {
        "name": "[Plan Anual] Nunca han reservado",
        "description": "Suscriptores con 0 visitas registradas. Objetivo: primera conversión.",
        "conditions": {
            "operator": "AND",
            "rules": [
                {"field": "opted_in", "op": "eq", "value": True},
                {"field": "veces_hotboat", "op": "eq", "value": 0},
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Campañas del plan anual — todas en draft, sin scheduled_at
# Formato nombre: [MES] Descripción — Segmento objetivo
# ---------------------------------------------------------------------------
CAMPAIGNS = [
    # ── ENERO ──────────────────────────────────────────────────────────────
    {
        "name": "[ENE] Upsell extras — clientes de temporada",
        "subject": "¿Le falta algo a tu día en el lago?",
        "preview_text": "Kayak, almuerzo, guía... todavía podés sumar extras a tu reserva.",
        "segment": "[Plan Anual] Clientes recurrentes (3+ visitas)",
    },
    {
        "name": "[ENE] Última oportunidad — indecisos",
        "subject": "Todavía quedan fechas en enero",
        "preview_text": "Cupos limitados. Si lo estabas pensando, este es el momento.",
        "segment": "[Plan Anual] Nunca han reservado",
    },
    {
        "name": "[ENE] Tus favoritos del verano — recurrentes",
        "subject": "Tus favoritos del verano pasado",
        "preview_text": "La última vez pediste esto. ¿Lo repetimos?",
        "segment": "[Plan Anual] Clientes recurrentes (3+ visitas)",
    },
    # ── FEBRERO ────────────────────────────────────────────────────────────
    {
        "name": "[FEB] Cierre de temporada — gracias",
        "subject": "Gracias por tu verano con HotBoat",
        "preview_text": "Fue una temporada increíble. Gracias por ser parte.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[FEB] Early bird verano 26-27 — VIP",
        "subject": "Reservá primero tu fecha del verano 26-27",
        "preview_text": "Acceso exclusivo antes de que abra al público. Solo para clientes VIP.",
        "segment": "[Plan Anual] Clientes VIP (5+ visitas)",
    },
    # ── MARZO ──────────────────────────────────────────────────────────────
    {
        "name": "[MAR] Lago en otoño — no han reservado",
        "subject": "El lago en otoño es diferente (y hay lugar)",
        "preview_text": "Menos gente, más tranquilidad, misma magia. Descubrilo.",
        "segment": "[Plan Anual] Nunca han reservado",
    },
    {
        "name": "[MAR] Win-back — hace tiempo que no vienen",
        "subject": "¿Qué pasó? Te extrañamos en el lago",
        "preview_text": "Vemos que hace un tiempo que no reservás. Queremos saber cómo estás.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[MAR] Teaser Semana Santa — todos",
        "subject": "Semana Santa en el lago — fechas abiertas",
        "preview_text": "Las fechas de Semana Santa ya están disponibles. Anotate.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    # ── ABRIL ──────────────────────────────────────────────────────────────
    {
        "name": "[ABR] Semana Santa — campaña principal",
        "subject": "Semana Santa en el lago: pocos cupos",
        "preview_text": "Quedan muy pocas fechas. No dejes para mañana lo que podés reservar hoy.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[ABR] Upsell alojamiento — Semana Santa",
        "subject": "Quedarse es diferente — alojamiento disponible",
        "preview_text": "Pernoctá en el lago y viví la experiencia completa esta Semana Santa.",
        "segment": "[Plan Anual] Sin alojamiento",
    },
    {
        "name": "[ABR] Acceso prioritario — recurrentes",
        "subject": "Tu reserva de Semana Santa, con prioridad",
        "preview_text": "Como cliente fiel, tenés acceso preferencial antes de que se agoten los cupos.",
        "segment": "[Plan Anual] Clientes recurrentes (3+ visitas)",
    },
    # ── MAYO ───────────────────────────────────────────────────────────────
    {
        "name": "[MAY] Behind the scenes — todos",
        "subject": "Qué estamos preparando para el invierno",
        "preview_text": "Mantenimiento, mejoras, novedades. Un vistazo al HotBoat que viene.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[MAY] Encuesta satisfacción — VIP",
        "subject": "Contanos qué mejoraría tu experiencia",
        "preview_text": "Tu opinión vale. Solo 3 preguntas rápidas.",
        "segment": "[Plan Anual] Clientes VIP (5+ visitas)",
    },
    # ── JUNIO ──────────────────────────────────────────────────────────────
    {
        "name": "[JUN] Lago en invierno — editorial",
        "subject": "El lago en invierno: fotos que no esperabas",
        "preview_text": "Niebla, silencio y colores que el verano no tiene. Mirá esto.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[JUN] Oferta invernal — clientes solo verano",
        "subject": "¿Sabías que el invierno tiene sus propias maravillas?",
        "preview_text": "HotBoat en invierno es otra experiencia. Te lo queremos mostrar.",
        "segment": "[Plan Anual] Clientes recurrentes (3+ visitas)",
    },
    # ── JULIO ──────────────────────────────────────────────────────────────
    {
        "name": "[JUL] Vacaciones de invierno — familias",
        "subject": "Vacaciones de invierno en el lago con los chicos",
        "preview_text": "Actividades para toda la familia. Julio en el lago es una experiencia única.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[JUL] Últimos cupos vacaciones invierno — todos",
        "subject": "Julio en el lago — últimos cupos de vacaciones",
        "preview_text": "Las vacaciones de invierno se están llenando. Quedan pocos lugares.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    # ── AGOSTO ─────────────────────────────────────────────────────────────
    {
        "name": "[AGO] Primavera se acerca — todos",
        "subject": "Se viene la primavera en el lago",
        "preview_text": "Las fechas de octubre ya están disponibles. Sé el primero en reservar.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[AGO] Win-back inactivos — hace 12 meses",
        "subject": "Hace un año que no nos vemos",
        "preview_text": "El lago te está esperando. ¿Nos contás qué pasó?",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    # ── SEPTIEMBRE ─────────────────────────────────────────────────────────
    {
        "name": "[SEP] Acceso anticipado 18 sept — VIP",
        "subject": "18 de septiembre en el lago — acceso anticipado",
        "preview_text": "Solo para clientes frecuentes. Reservá antes de que abra al público.",
        "segment": "[Plan Anual] Clientes VIP (5+ visitas)",
    },
    {
        "name": "[SEP] Fiestas Patrias — campaña principal",
        "subject": "Fiestas Patrias en HotBoat: quedan X cupos",
        "preview_text": "El 18 en el lago es una tradición. No te quedes sin lugar.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[SEP] Alojamiento Fiestas Patrias — sin hospedaje",
        "subject": "Quédate a celebrar el 18 con nosotros",
        "preview_text": "Pernoctá en el lago y viví las Fiestas Patrias como nunca.",
        "segment": "[Plan Anual] Sin alojamiento",
    },
    # ── OCTUBRE ────────────────────────────────────────────────────────────
    {
        "name": "[OCT] Apertura temporada verano — anticipación",
        "subject": "La temporada de verano ya tiene fecha",
        "preview_text": "Anotate en la lista de espera y sé el primero en elegir tu fecha.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[OCT] Pre-sale exclusivo verano — VIP",
        "subject": "Tus fechas de verano, antes de que abra al público",
        "preview_text": "48 horas de ventaja exclusiva para nuestros clientes más fieles.",
        "segment": "[Plan Anual] Clientes VIP (5+ visitas)",
    },
    {
        "name": "[OCT] ¿Volvés este verano? — clientes anteriores",
        "subject": "¿Volvés este verano?",
        "preview_text": "El verano pasado fuiste en [mes]. Este año, ¿cuándo te anotamos?",
        "segment": "[Plan Anual] Clientes recurrentes (3+ visitas)",
    },
    # ── NOVIEMBRE ──────────────────────────────────────────────────────────
    {
        "name": "[NOV] Lanzamiento temporada alta — reservas abiertas",
        "subject": "Las reservas de verano están abiertas",
        "preview_text": "Ya podés elegir tu fecha. Diciembre y enero son los primeros en llenarse.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[NOV] Urgencia cupos verano — todos",
        "subject": "Diciembre y enero casi llenos",
        "preview_text": "Quedan muy pocas fechas en diciembre. Enero también se está llenando.",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
    {
        "name": "[NOV] Bundle completo — sin alojamiento",
        "subject": "Este verano, la experiencia completa",
        "preview_text": "Embarcación + alojamiento en el lago. Una experiencia diferente.",
        "segment": "[Plan Anual] Sin alojamiento",
    },
    # ── DICIEMBRE ──────────────────────────────────────────────────────────
    {
        "name": "[DIC] Últimas fechas disponibles — indecisos",
        "subject": "Las últimas fechas de diciembre",
        "preview_text": "Si lo estabas pensando, estas son las últimas fechas de diciembre.",
        "segment": "[Plan Anual] Nunca han reservado",
    },
    {
        "name": "[DIC] Pre-arrival — reservaron diciembre",
        "subject": "Tu día en el lago se acerca — lo que necesitás saber",
        "preview_text": "Todo lo que tenés que saber antes de llegar. Te lo contamos.",
        "segment": "[Plan Anual] Clientes recurrentes (3+ visitas)",
    },
    {
        "name": "[DIC] Felices fiestas — todos",
        "subject": "Felices fiestas del equipo HotBoat",
        "preview_text": "Gracias por ser parte de este año. ¡Hasta el próximo verano!",
        "segment": "[Plan Anual] Todos los suscriptores",
    },
]


def upsert_segments(session: Session) -> dict[str, int]:
    """Crea o actualiza los segmentos del plan anual. Devuelve {nombre: id}."""
    name_to_id = {}
    for seg_data in SEGMENTS:
        existing = session.exec(
            select(Segment).where(Segment.name == seg_data["name"])
        ).first()
        if existing:
            existing.description = seg_data["description"]
            existing.conditions = seg_data["conditions"]
            session.add(existing)
            seg_id = existing.id
            print(f"  ✓ Segmento actualizado: {seg_data['name']}")
        else:
            seg = Segment(**seg_data)
            session.add(seg)
            session.flush()
            seg_id = seg.id
            print(f"  + Segmento creado:     {seg_data['name']}")
        name_to_id[seg_data["name"]] = seg_id
    session.commit()
    return name_to_id


def get_fallback_template(session: Session) -> int:
    """Devuelve el ID del primer template disponible."""
    tmpl = session.exec(select(Template)).first()
    if not tmpl:
        raise RuntimeError(
            "No hay ningún template en la base de datos. "
            "Creá al menos uno desde el panel antes de correr este script."
        )
    return tmpl.id


def create_campaigns(session: Session, seg_map: dict[str, int], fallback_template_id: int) -> None:
    """Crea las campañas del plan anual como draft si no existen aún."""
    created = 0
    skipped = 0
    for camp_data in CAMPAIGNS:
        existing = session.exec(
            select(Campaign).where(Campaign.name == camp_data["name"])
        ).first()
        if existing:
            print(f"  - Ya existe: {camp_data['name']}")
            skipped += 1
            continue

        seg_id = seg_map.get(camp_data["segment"])
        if not seg_id:
            print(f"  ✗ Segmento no encontrado para: {camp_data['name']}")
            continue

        campaign = Campaign(
            name=camp_data["name"],
            subject=camp_data["subject"],
            preview_text=camp_data.get("preview_text"),
            template_id=fallback_template_id,
            segment_id=seg_id,
            status="draft",
        )
        session.add(campaign)
        print(f"  + Campaña creada: {camp_data['name']}")
        created += 1

    session.commit()
    print(f"\n  Resumen: {created} creadas, {skipped} ya existían.")


def main():
    print("\n=== Seed: Plan Anual HotBoat 2026 ===\n")

    with Session(engine) as session:
        print("Segmentos:")
        seg_map = upsert_segments(session)

        print("\nTemplate de referencia:")
        tmpl_id = get_fallback_template(session)
        print(f"  Usando template ID {tmpl_id} como placeholder.")
        print("  IMPORTANTE: Asigná el template correcto a cada campaña desde el panel.\n")

        print("Campañas:")
        create_campaigns(session, seg_map, tmpl_id)

    print("\n=== Listo ===")
    print("Las campañas están en estado 'draft'.")
    print("Para activarlas: asignar template correcto + scheduled_at y cambiar status a 'scheduled'.\n")


if __name__ == "__main__":
    main()
