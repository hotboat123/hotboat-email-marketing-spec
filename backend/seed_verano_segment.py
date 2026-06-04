"""
Crea el segmento 'Clientes de verano (temporada 25/26)' y actualiza
las campañas del plan anual que deben apuntar a clientes de verano.
Ejecutar: python seed_verano_segment.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import Session, select, create_engine
from app.core.config import settings
from app.models.user import User          # noqa
from app.models.contact import Contact    # noqa
from app.models.segment import Segment
from app.models.template import Template  # noqa
from app.models.campaign import Campaign
from app.models.automation import Automation, AutomationRun  # noqa
from app.models.form import SignupForm    # noqa

engine = create_engine(settings.DATABASE_URL)

SEGMENT_NAME = "Clientes de verano (temporada 25/26)"

SEGMENT_CONDITIONS = {
    "operator": "AND",
    "rules": [
        {"field": "ultima_visita", "op": "gte", "value": "2025-12-01"},
        {"field": "ultima_visita", "op": "lte", "value": "2026-02-28"},
    ],
}

# Campañas que deben usar este segmento
CAMPAIGNS_TO_UPDATE = [
    "[ENE] Upsell extras — clientes de temporada",
    "[ENE] Tus favoritos del verano — recurrentes",
    "[JUN] Oferta invernal — clientes solo verano",
]


def main():
    print("\n=== Segmento: Clientes de verano (temporada 25/26) ===\n")

    with Session(engine) as session:
        # Crear o actualizar el segmento
        existing = session.exec(
            select(Segment).where(Segment.name == SEGMENT_NAME)
        ).first()

        if existing:
            existing.conditions = SEGMENT_CONDITIONS
            existing.description = (
                "Contactos cuya última visita fue entre el 01/12/2025 y el 28/02/2026 "
                "(temporada de verano en Chile). Útil para upsell en temporada alta y "
                "para reactivar en invierno a quienes vinieron en verano."
            )
            session.add(existing)
            session.flush()
            seg_id = existing.id
            print(f"  ✓ Segmento actualizado (ID {seg_id}): {SEGMENT_NAME}")
        else:
            seg = Segment(
                name=SEGMENT_NAME,
                description=(
                    "Contactos cuya última visita fue entre el 01/12/2025 y el 28/02/2026 "
                    "(temporada de verano en Chile). Útil para upsell en temporada alta y "
                    "para reactivar en invierno a quienes vinieron en verano."
                ),
                conditions=SEGMENT_CONDITIONS,
            )
            session.add(seg)
            session.flush()
            seg_id = seg.id
            print(f"  + Segmento creado (ID {seg_id}): {SEGMENT_NAME}")

        session.commit()

        # Actualizar campañas
        print(f"\n  Actualizando campañas al segmento ID {seg_id}:\n")
        for camp_name in CAMPAIGNS_TO_UPDATE:
            campaign = session.exec(
                select(Campaign).where(Campaign.name == camp_name)
            ).first()
            if not campaign:
                print(f"  ✗ No encontrada: {camp_name}")
                continue
            campaign.segment_id = seg_id
            session.add(campaign)
            print(f"  ✓ ID {campaign.id:3d} — {camp_name}")

        session.commit()

    print("\n=== Listo ===")
    print(f"  Recordá actualizar las fechas del segmento cada temporada.")
    print(f"  Próximo verano cambiar a: 2026-12-01 / 2027-02-28\n")


if __name__ == "__main__":
    main()
