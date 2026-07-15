import csv
import io
import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, text
from sqlmodel import Session, select

from app.database import get_session
from app.core.deps import get_current_user, require_editor
from app.models.user import User
from app.models.contact_crm import ContactCRM, ContactCRMRead, CallStatusUpdate
from app.models.call_activity import CallActivity, CallActivityRead
from app.models.score_weight import ScoreWeight, ScoreWeightRead, ScoreWeightUpdate
from app.services.sync_hotboat import _source_engine
from app.services.crm_sync import SCORE_WEIGHTS, SCORE_WEIGHT_LABELS

router = APIRouter()

VALID_CALL_STATUSES = {"pending", "called", "no_answer", "booked", "not_interested"}


SORT_COLUMNS = {
    "score": ContactCRM.reservation_score,
    "last_interaction": ContactCRM.last_interaction_at,  # ultimo mensaje de WhatsApp
    "booking": ContactCRM.ultima_visita,  # ultima reserva confirmada
}


_ANON_ROW_DEFAULTS = dict(
    phone=None, email=None, linked_contact_id=None,
    ad_source=None, ad_platform=None, ad_creative_url=None, utm_campaign=None,
    lead_status=None, last_interaction_at=None,
    veces_hotboat=0, veces_pendiente=0, ultima_visita=None, ticket_medio=None,
    extras_favoritos=None, reservation_score=None, score_updated_at=None,
    score_breakdown=None, call_status="anonymous", call_status_updated_at=None,
    link_clicked=False, link_viewed_prices=False, link_selected_date=False,
    link_last_seen_at=None, web_session_count=1,
    channel_whatsapp_link=False, channel_direct_web=True,
    is_anonymous=True,
)


def _anon_session_id_to_int(session_id: str) -> int:
    """Stable negative synthetic id so anonymous rows never collide with a
    real contacts_crm id (a positive serial)."""
    import hashlib
    return -int(hashlib.md5(session_id.encode()).hexdigest()[:8], 16)


def _count_anonymous_visitors() -> int:
    engine = _source_engine()
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT DISTINCT session_id FROM booking_visitor_sessions
                WHERE session_id NOT IN (SELECT session_id FROM booking_visitor_identity)
            ) sub
        """)).scalar_one()


def _fetch_anonymous_visitors(skip: int, limit: int) -> List[dict]:
    """Anonymous website visitors (no phone/email captured) as rows shaped
    like ContactCRMRead, sourced from hotboat-whatsapp's booking_visitor_sessions.
    One row per unique session_id (its latest snapshot), excluding sessions
    already linked to a real phone in booking_visitor_identity — those already
    show up as normal contacts_crm rows via channel_direct_web."""
    if limit <= 0:
        return []
    engine = _source_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT * FROM (
                SELECT DISTINCT ON (session_id)
                    session_id, classification, classification_desc,
                    event_count, referrer, started_at
                FROM booking_visitor_sessions
                WHERE session_id NOT IN (SELECT session_id FROM booking_visitor_identity)
                ORDER BY session_id, started_at DESC
            ) sub
            ORDER BY started_at DESC
            OFFSET :skip LIMIT :limit
        """), {"skip": skip, "limit": limit}).all()

    out = []
    for r in rows:
        out.append({
            **_ANON_ROW_DEFAULTS,
            "id": _anon_session_id_to_int(r.session_id),
            "session_id": r.session_id,
            "name": "Visitante anónimo",
            "web_classification": r.classification,
            "web_classification_desc": r.classification_desc,
            "web_last_seen_at": r.started_at,
            "created_at": r.started_at,
            "updated_at": r.started_at,
        })
    return out


def _apply_filters(query, call_status, min_score, ad_source, q):
    if call_status:
        query = query.where(ContactCRM.call_status == call_status)
    if min_score is not None:
        query = query.where(ContactCRM.reservation_score >= min_score)
    if ad_source:
        query = query.where(ContactCRM.ad_source.ilike(f"%{ad_source}%"))
    if q:
        # El teléfono se compara solo por dígitos (mismo criterio E.164 del
        # resto del sync) para que buscar "977577307" matchee "+56977577307".
        digits = re.sub(r"\D", "", q)
        conditions = [ContactCRM.name.ilike(f"%{q}%")]
        if digits:
            conditions.append(func.regexp_replace(ContactCRM.phone, r"[^0-9]", "", "g").ilike(f"%{digits}%"))
        query = query.where(or_(*conditions))
    return query


_EPOCH = datetime(1970, 1, 1)


def _naive(dt: Optional[datetime]) -> datetime:
    """contacts_crm timestamps come back tz-naive, booking_visitor_sessions'
    tz-aware (UTC) — strip tzinfo so both sides can be compared/sorted."""
    if dt is None:
        return _EPOCH
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _fetch_recent_activity(session: Session, query, skip: int, limit: int, include_anon: bool) -> List[dict]:
    """"Actividad reciente" sort — interleaves real contacts and anonymous
    website visits by their own most-recent-touch timestamp, most recent
    first. Plain SORT_COLUMNS sorts (score/last_interaction/booking) can't
    do this: with every contacts_crm row already scored, appending
    anonymous rows only after the real ones run out buried them ~160 pages
    deep. Fetches the top (skip+limit) candidates from each source
    pre-sorted by recency in SQL, merge-sorts them in Python, then slices —
    avoids a fragile hand-written cross-table UNION."""
    fetch_n = skip + limit
    recency = func.greatest(
        func.coalesce(ContactCRM.last_interaction_at, _EPOCH),
        func.coalesce(ContactCRM.web_last_seen_at, _EPOCH),
    )
    real_rows = session.exec(query.order_by(recency.desc()).limit(fetch_n)).all()
    merged: List[dict] = []
    for c in real_rows:
        d = c.model_dump()
        d["_sort_ts"] = max(_naive(c.last_interaction_at), _naive(c.web_last_seen_at))
        merged.append(d)

    # A min_score/call_status/q filter has no meaning for an anonymous
    # visitor (no score, never in the call queue) — leave them out rather
    # than show rows that don't actually match what was asked for.
    if include_anon:
        anon_rows = _fetch_anonymous_visitors(0, fetch_n)
        for d in anon_rows:
            d["_sort_ts"] = _naive(d["web_last_seen_at"])
        merged.extend(anon_rows)

    merged.sort(key=lambda d: d["_sort_ts"], reverse=True)
    page = merged[skip: skip + limit]
    for d in page:
        d.pop("_sort_ts", None)
    return page


@router.get("/contacts", response_model=List[ContactCRMRead])
def list_crm_contacts(
    call_status: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    ad_source: Optional[str] = None,
    q: Optional[str] = Query(None, description="Busca por nombre o teléfono"),
    sort: str = Query("score", pattern="^(score|last_interaction|booking|recent)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    query = _apply_filters(select(ContactCRM), call_status, min_score, ad_source, q)
    filtered = bool(call_status or min_score is not None or ad_source or q)

    if sort == "recent":
        return _fetch_recent_activity(session, query, skip, limit, include_anon=not filtered)

    ordered = query.order_by(SORT_COLUMNS[sort].desc().nullslast())
    contacts = session.exec(ordered.offset(skip).limit(limit)).all()
    result: List[dict] = [c.model_dump() for c in contacts]

    # Anonymous website visits only make sense to mix in when browsing the
    # unfiltered queue — a "score >= 60" or call_status filter has no
    # meaning for someone who was never scored or ever put in the queue.
    # They're appended after all real contacts are exhausted, sorted by
    # most recent visit, and keep paginating from there on later pages.
    if not filtered:
        remaining = limit - len(result)
        if remaining > 0:
            total_real = session.exec(
                select(func.count()).select_from(query.subquery())
            ).one()
            anon_skip = max(0, skip - total_real)
            result.extend(_fetch_anonymous_visitors(anon_skip, remaining))

    return result


@router.get("/anonymous-visits/{session_id}")
def get_anonymous_visit(
    session_id: str,
    _: User = Depends(get_current_user),
):
    """Event-by-event detail of one anonymous website visit (what an
    unidentified visitor actually did), for the Llamadas drill-down click."""
    engine = _source_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT session_id, classification, classification_desc, referrer,
                   is_returning, started_at, ended_at, events_json
            FROM booking_visitor_sessions
            WHERE session_id = :sid
            ORDER BY started_at DESC
            LIMIT 1
        """), {"sid": session_id}).first()

    if not row:
        raise HTTPException(status_code=404, detail="Visita no encontrada")

    return {
        "session_id": row.session_id,
        "classification": row.classification,
        "classification_desc": row.classification_desc,
        "referrer": row.referrer,
        "is_returning": row.is_returning,
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "events": row.events_json or [],
    }


@router.get("/contacts/export/csv")
def export_crm_contacts_csv(
    call_status: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    query = select(ContactCRM)
    if call_status:
        query = query.where(ContactCRM.call_status == call_status)
    if min_score is not None:
        query = query.where(ContactCRM.reservation_score >= min_score)
    query = query.order_by(ContactCRM.reservation_score.desc().nullslast())
    contacts = session.exec(query).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "phone", "name", "email", "reservation_score", "call_status",
        "ad_source", "veces_hotboat", "last_interaction_at", "ultima_visita",
    ])
    for c in contacts:
        writer.writerow([
            c.phone, c.name, c.email, c.reservation_score, c.call_status,
            c.ad_source, c.veces_hotboat, c.last_interaction_at, c.ultima_visita,
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=crm_contacts.csv"},
    )


@router.get("/contacts/by_contact/{contact_id}", response_model=ContactCRMRead)
def get_crm_by_contact(
    contact_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Busca el registro CRM (WhatsApp/telefono) vinculado a un contacto de email,
    para poder mostrar ambas vistas fusionadas en /contacts/{id}."""
    contact = session.exec(select(ContactCRM).where(ContactCRM.linked_contact_id == contact_id)).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Sin registro CRM vinculado")
    return contact


@router.get("/contacts/{contact_crm_id}", response_model=ContactCRMRead)
def get_crm_contact(
    contact_crm_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return contact


@router.get("/contacts/{contact_crm_id}/call_activity", response_model=List[CallActivityRead])
def get_call_activity(
    contact_crm_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return session.exec(
        select(CallActivity)
        .where(CallActivity.contact_crm_id == contact_crm_id)
        .order_by(CallActivity.created_at.desc())
    ).all()


@router.get("/contacts/{contact_crm_id}/conversations")
def get_crm_conversations(
    contact_crm_id: int,
    limit: int = Query(100, le=500),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Historial de mensajes de WhatsApp para este contacto (lectura directa de
    hotboat-whatsapp). Compara con y sin '+' porque los mensajes anteriores al
    backfill de normalizacion de telefono quedaron guardados sin el '+'."""
    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    if not contact.phone:
        return []

    phone_digits = contact.phone.lstrip("+")
    engine = _source_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT message_text, response_text, message_type, direction, created_at
            FROM whatsapp_conversations
            WHERE phone_number IN (:phone, :phone_digits)
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"phone": contact.phone, "phone_digits": phone_digits, "limit": limit}).fetchall()

    return [
        {
            "message_text": r.message_text,
            "response_text": r.response_text,
            "message_type": r.message_type,
            "direction": r.direction,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/contacts/{contact_crm_id}/web_activity")
def get_crm_web_activity(
    contact_crm_id: int,
    limit: int = Query(200, le=1000),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Eventos de navegacion web para este contacto. Combina las dos formas de
    identidad que hoy existen en hotboat-whatsapp:
    - link_token (tracked_quote_links): cubre a quien el bot le mando un link.
    - booking_visitor_identity (session_id/visitor_id): cubre a quien llego
      directo a la web (hotboat.cl, ads, organico) y quedo identificado al
      reservar — sin haber pasado nunca por un link de WhatsApp."""
    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    if not contact.phone:
        return []

    phone_digits = contact.phone.lstrip("+")
    engine = _source_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT DISTINCT bve.event_type, bve.extra_date, bve.time_label,
                       bve.recorded_at, bve.session_id
                FROM booking_visitor_events bve
                WHERE bve.link_token IN (
                    SELECT token FROM tracked_quote_links WHERE phone IN (:phone, :phone_digits)
                ) OR bve.session_id IN (
                    SELECT session_id FROM booking_visitor_identity WHERE phone IN (:phone, :phone_digits)
                ) OR bve.visitor_id IN (
                    SELECT visitor_id FROM booking_visitor_identity
                    WHERE phone IN (:phone, :phone_digits) AND visitor_id IS NOT NULL
                )
                ORDER BY bve.recorded_at DESC
                LIMIT :limit
            """), {"phone": contact.phone, "phone_digits": phone_digits, "limit": limit}).fetchall()
    except Exception:
        # Tabla/columnas pueden no existir aun en algunos entornos — no romper
        # el detalle del contacto.
        return []

    return [
        {
            "event_type": r.event_type,
            "extra_date": r.extra_date,
            "time_label": r.time_label,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            "session_id": r.session_id,
        }
        for r in rows
    ]


@router.patch("/contacts/{contact_crm_id}/call_status", response_model=ContactCRMRead)
def update_call_status(
    contact_crm_id: int,
    payload: CallStatusUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(require_editor),
):
    if payload.call_status not in VALID_CALL_STATUSES:
        raise HTTPException(status_code=400, detail=f"call_status inválido. Válidos: {sorted(VALID_CALL_STATUSES)}")

    contact = session.get(ContactCRM, contact_crm_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")

    old_status = contact.call_status
    now = datetime.utcnow()
    contact.call_status = payload.call_status
    contact.call_status_updated_at = now
    contact.updated_at = now
    session.add(contact)
    session.add(CallActivity(
        contact_crm_id=contact_crm_id,
        old_status=old_status,
        new_status=payload.call_status,
        note=payload.note,
        created_by=payload.created_by or getattr(user, "email", None),
        created_at=now,
    ))
    session.commit()
    session.refresh(contact)
    return contact


def _funnel_row(total: int, viewed_prices: int, selected_date: int, pending: int, paid: int) -> dict:
    return {
        "total": total,
        "viewed_prices": viewed_prices,
        "selected_date": selected_date,
        "pending_payment": pending,
        "paid": paid,
        "conversion_rate": round(paid / total * 100, 1) if total else 0.0,
    }


def _ad_spend_by_name() -> dict:
    """Gasto/CPC/costo por conversación real por anuncio de Meta, leído de
    meta_ads_insights (misma Postgres compartida — un ETL aparte importa esto
    directo desde la Marketing API de Meta). Se cruza por nombre de anuncio
    contra contacts_crm.ad_source; no todos matchean — algunos ad_source son
    canales autoreportados ("TV", "TripAdvisor", "boca a boca") que nunca
    fueron un anuncio de Meta con gasto asociado, y esos quedan sin dato."""
    try:
        engine = _source_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT a.name AS ad_name,
                       MIN(a.id) AS ad_id,
                       SUM(i.spend) AS spend,
                       SUM(i.clicks) AS clicks,
                       SUM(meta_fn_action_types_sum(i.actions, ARRAY[
                           'onsite_conversion.messaging_conversation_started_7d',
                           'onsite_conversion.messaging_conversation_started',
                           'messaging_conversation_started'
                       ])) AS conversations_started
                FROM meta_ads_insights i
                LEFT JOIN meta_ads a ON a.id = i.ad_id
                WHERE a.name IS NOT NULL
                GROUP BY a.name
            """)).all()
    except Exception:
        # meta_ads_insights/meta_ads pueden no existir en algunos entornos — no
        # bloquear el resto del embudo por esto.
        return {}

    result = {}
    for r in rows:
        spend = float(r.spend or 0)
        clicks = float(r.clicks or 0)
        conversations = float(r.conversations_started or 0)
        result[r.ad_name.strip().lower()] = {
            "ad_id": r.ad_id,
            "spend": round(spend),
            "cpc": round(spend / clicks, 1) if clicks else None,
            "cost_per_conversation": round(spend / conversations, 1) if conversations else None,
        }
    return result


@router.get("/analytics/funnel")
def get_funnel_analytics(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Embudo (vio precios -> eligió fecha -> por pagar -> pago confirmado)
    agrupado por anuncio y por canal de llegada (WhatsApp vs web directo). Usa
    los campos ya fusionados por crm_sync (link_viewed_prices/link_selected_date/
    veces_hotboat/veces_pendiente) y los dos flags de origen
    (channel_whatsapp_link/channel_direct_web), sin duplicar la lógica de conteo.
    veces_hotboat solo cuenta pago confirmado — veces_pendiente son reservas
    web que todavía están esperando pago (existen hasta 120 min antes del
    auto-cleanup en hotboat-whatsapp)."""
    by_ad_rows = session.execute(text("""
        SELECT COALESCE(NULLIF(ad_source, ''), 'Sin anuncio') AS ad_source,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE link_viewed_prices) AS viewed_prices,
               COUNT(*) FILTER (WHERE link_selected_date)  AS selected_date,
               COUNT(*) FILTER (WHERE veces_pendiente > 0) AS pending,
               COUNT(*) FILTER (WHERE veces_hotboat > 0)   AS paid
        FROM contacts_crm
        GROUP BY 1
        ORDER BY total DESC
        LIMIT 20
    """)).all()

    by_channel_rows = session.execute(text("""
        SELECT 'WhatsApp' AS channel, COUNT(*) AS total,
               COUNT(*) FILTER (WHERE link_viewed_prices) AS viewed_prices,
               COUNT(*) FILTER (WHERE link_selected_date)  AS selected_date,
               COUNT(*) FILTER (WHERE veces_pendiente > 0) AS pending,
               COUNT(*) FILTER (WHERE veces_hotboat > 0)   AS paid
        FROM contacts_crm WHERE channel_whatsapp_link
        UNION ALL
        SELECT 'Web directo', COUNT(*),
               COUNT(*) FILTER (WHERE link_viewed_prices),
               COUNT(*) FILTER (WHERE link_selected_date),
               COUNT(*) FILTER (WHERE veces_pendiente > 0),
               COUNT(*) FILTER (WHERE veces_hotboat > 0)
        FROM contacts_crm WHERE channel_direct_web
    """)).all()

    ad_spend = _ad_spend_by_name()
    no_spend_data = {"ad_id": None, "spend": None, "cpc": None, "cost_per_conversation": None}

    return {
        "by_ad_source": [
            {
                "ad_source": r.ad_source,
                **_funnel_row(r.total, r.viewed_prices, r.selected_date, r.pending, r.paid),
                **ad_spend.get(r.ad_source.strip().lower(), no_spend_data),
            }
            for r in by_ad_rows
        ],
        "by_channel": [
            {"channel": r.channel, **_funnel_row(r.total, r.viewed_prices, r.selected_date, r.pending, r.paid)}
            for r in by_channel_rows
        ],
    }


def _seed_missing_score_weights(session: Session, existing_rows: list) -> list:
    """Inserta cualquier clave de SCORE_WEIGHTS que todavia no este en la tabla —
    tanto la primera vez (tabla vacia) como cuando se agrega una regla nueva al
    código después de que alguien ya edito el panel (tabla parcialmente sembrada)."""
    now = datetime.utcnow()
    have = {r.key for r in existing_rows}
    missing = [
        ScoreWeight(key=key, label=SCORE_WEIGHT_LABELS.get(key, key), points=points, updated_at=now)
        for key, points in SCORE_WEIGHTS.items()
        if key not in have
    ]
    if not missing:
        return existing_rows
    for row in missing:
        session.add(row)
    session.commit()
    return session.exec(select(ScoreWeight)).all()


@router.get("/score-weights", response_model=List[ScoreWeightRead])
def list_score_weights(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Puntos que usa reservation_score (crm_sync._compute_score). Si nunca se
    editaron desde el dashboard, siembra la tabla con los defaults de crm_sync.py
    para que el panel de Configuración parta con valores sensatos."""
    rows = _seed_missing_score_weights(session, session.exec(select(ScoreWeight)).all())
    return sorted(rows, key=lambda r: -r.points)


@router.put("/score-weights", response_model=List[ScoreWeightRead])
def update_score_weights(
    payload: List[ScoreWeightUpdate],
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    """Guarda los puntos editados. Los toma el próximo crm_sync — no recalcula
    scores existentes al toque, para no bloquear la request con un sync completo."""
    now = datetime.utcnow()
    existing_rows = _seed_missing_score_weights(session, session.exec(select(ScoreWeight)).all())
    by_key = {r.key: r for r in existing_rows}
    for item in payload:
        row = by_key.get(item.key)
        if not row:
            continue  # ignora claves desconocidas — no crea reglas nuevas desde el frontend
        row.points = item.points
        row.updated_at = now
        session.add(row)
    session.commit()
    rows = session.exec(select(ScoreWeight)).all()
    return sorted(rows, key=lambda r: -r.points)
