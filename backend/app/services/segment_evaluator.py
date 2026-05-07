from typing import List, Optional, Any
from sqlalchemy import and_, or_, func
from sqlmodel import Session, select
from app.models.contact import Contact

# Campos permitidos en condiciones de segmento
FIELD_MAP = {
    "email":          Contact.email,
    "language":       Contact.language,
    "origin_utm":     Contact.origin_utm,
    "opted_in":       Contact.opted_in,
    "veces_hotboat":  Contact.veces_hotboat,
    "ultima_visita":  Contact.ultima_visita,
    "ha_alojamiento": Contact.ha_alojamiento,
    "ticket_medio":   Contact.ticket_medio,
    "name":           Contact.name,
}

OPS = {
    "eq":       lambda col, v: col == v,
    "neq":      lambda col, v: col != v,
    "gt":       lambda col, v: col > v,
    "gte":      lambda col, v: col >= v,
    "lt":       lambda col, v: col < v,
    "lte":      lambda col, v: col <= v,
    "contains": lambda col, v: col.ilike(f"%{v}%"),
    "starts":   lambda col, v: col.ilike(f"{v}%"),
    "in":       lambda col, v: col.in_(v),
    "is_null":  lambda col, v: col.is_(None),
    "not_null": lambda col, v: col.isnot(None),
}


def _build_clause(node: dict) -> Optional[Any]:
    """Convierte un nodo de condiciones en un cláusula SQLAlchemy."""
    if "rules" in node:
        operator = node.get("operator", "AND").upper()
        sub_clauses = [_build_clause(r) for r in node["rules"]]
        sub_clauses = [c for c in sub_clauses if c is not None]
        if not sub_clauses:
            return None
        return and_(*sub_clauses) if operator == "AND" else or_(*sub_clauses)

    field = node.get("field")
    op = node.get("op")
    value = node.get("value")

    # Soporte para custom_fields.{clave} — p. ej. custom_fields.es_mama
    if field and field.startswith("custom_fields."):
        key = field[len("custom_fields."):]
        col = Contact.custom_fields[key].astext
        fn = OPS.get(op)
        if fn is None:
            return None
        # Los booleanos se almacenan como texto en JSON ("true"/"false")
        if isinstance(value, bool):
            value = "true" if value else "false"
        return fn(col, value)

    col = FIELD_MAP.get(field)
    fn = OPS.get(op)
    if col is None or fn is None:
        return None

    return fn(col, value)


def evaluate_segment(conditions: Optional[dict], session: Session) -> List[Contact]:
    """Retorna contactos que coinciden con las condiciones del segmento (opted_in=True)."""
    query = select(Contact).where(Contact.opted_in == True)  # noqa: E712
    if conditions:
        clause = _build_clause(conditions)
        if clause is not None:
            query = query.where(clause)
    return list(session.exec(query).all())


def count_segment(conditions: Optional[dict], session: Session) -> int:
    query = select(func.count(Contact.id)).where(Contact.opted_in == True)  # noqa: E712
    if conditions:
        clause = _build_clause(conditions)
        if clause is not None:
            query = query.where(clause)
    return session.exec(query).one()
