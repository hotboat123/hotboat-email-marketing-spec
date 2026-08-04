"""
Unified sent-email log — combines campaign sends and automation runs into
a single, filterable, sortable, paginated view (mirrors the "Correos
enviados" page from the sibling Happy Lápiz product). A raw SQL UNION ALL
over both tables (rather than two ORM queries merged in Python) is what
makes global sorting + pagination correct and cheap across the current
~15k+ rows — Postgres does the work, not this process.

`provider` (SES vs Resend) isn't a stored column on either table — adding
one would need a migration and can't be back-filled for historical rows
anyway. Instead it's derived from resend_id length: Resend's ids are
always a 36-char UUID; SES's (sesv2) are much longer
(hex-hyphen-uuid-hyphen-seq, ~59-70 chars). Good enough to answer "how much
do I owe for SES" without a schema change.

ses_count/resend_count in the response are computed from every filter
EXCEPT provider (date range, search, origin, status still apply) — so
picking a date range shows "how many SES sends in this window" regardless
of whether the provider dropdown itself is set, which is the number that
actually matters for reading an AWS bill.
"""
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session

from app.database import get_session
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()

_SES_ID_MIN_LEN = 45  # Resend ids are 36 chars; SES sesv2 ids are ~59-70

_UNIFIED_CTE = """
WITH unified AS (
    SELECT
        cs.id AS row_id,
        'campaign' AS source_type,
        c.name AS source_name,
        COALESCE(ct.email, cs.to_email) AS email,
        cs.sent_at AS at,
        COALESCE(cs.rendered_subject, c.subject) AS subject,
        cs.status AS status,
        cs.resend_id AS resend_id
    FROM campaign_sends cs
    JOIN campaigns c ON c.id = cs.campaign_id
    LEFT JOIN contacts ct ON ct.id = cs.contact_id
    WHERE cs.sent_at IS NOT NULL

    UNION ALL

    SELECT
        ar.id AS row_id,
        'automation' AS source_type,
        a.name AS source_name,
        ar.contact_email AS email,
        ar.triggered_at AS at,
        COALESCE(ar.rendered_subject, a.subject) AS subject,
        CASE
            WHEN ar.status != 'sent' THEN ar.status
            WHEN ar.opened_at IS NOT NULL THEN 'opened'
            WHEN ar.clicked_at IS NOT NULL THEN 'clicked'
            WHEN ar.bounced_at IS NOT NULL THEN 'bounced'
            WHEN ar.delivered_at IS NOT NULL THEN 'delivered'
            ELSE ar.status
        END AS status,
        ar.resend_id AS resend_id
    FROM automation_runs ar
    JOIN automations a ON a.id = ar.automation_id
    WHERE ar.status != 'skipped'

    UNION ALL

    -- Todo lo que send_email() manda que NO tiene su propia fila de
    -- CampaignSend/AutomationRun (avisos de desuscripción, alertas internas
    -- al admin, y cualquier envío futuro que no agregue su propio tracking)
    -- — ver _TRACKED_ELSEWHERE en app/email/send_email.py.
    SELECT
        el.id AS row_id,
        'other' AS source_type,
        el.trigger AS source_name,
        el.to_email AS email,
        el.created_at AS at,
        el.subject AS subject,
        CASE WHEN el.sent THEN 'sent' ELSE 'failed' END AS status,
        el.message_id AS resend_id
    FROM email_log el
)
"""

# Whitelisted — never interpolate the raw sort_by/sort_dir query params into SQL.
_SORT_COLUMNS = {
    "at": "at",
    "email": "email",
    "subject": "subject",
    "origin": "source_type",
    "status": "status",
}


class SentEmailRow(BaseModel):
    id: int
    source_type: str
    source_name: str
    email: str
    at: Optional[datetime]
    subject: str
    status: str
    provider: str


class SentEmailsPage(BaseModel):
    items: List[SentEmailRow]
    total: int
    ses_count: int
    resend_count: int


def _build_where(
    *, email, subject, origin, status, date_from, date_to, include_provider, provider,
) -> tuple[list, dict]:
    where = []
    params: dict = {}

    if email:
        where.append("email ILIKE :email")
        params["email"] = f"%{email}%"
    if subject:
        where.append("subject ILIKE :subject")
        params["subject"] = f"%{subject}%"
    if origin in ("campaign", "automation", "other"):
        where.append("source_type = :origin")
        params["origin"] = origin
    if status:
        where.append("status = :status")
        params["status"] = status
    if date_from:
        where.append("at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where.append("at < :date_to_excl")
        params["date_to_excl"] = date_to + timedelta(days=1)
    if include_provider and provider in ("ses", "resend"):
        if provider == "ses":
            where.append(f"LENGTH(resend_id) >= {_SES_ID_MIN_LEN}")
        else:
            where.append(f"(resend_id IS NOT NULL AND LENGTH(resend_id) < {_SES_ID_MIN_LEN})")

    return where, params


@router.get("", response_model=SentEmailsPage)
def list_sent_emails(
    email: Optional[str] = Query(None, description="Búsqueda parcial en el email del destinatario"),
    subject: Optional[str] = Query(None, description="Búsqueda parcial en el asunto"),
    origin: Optional[str] = Query(None, description="'campaign' o 'automation'"),
    status: Optional[str] = Query(None),
    provider: Optional[str] = Query(None, description="'ses' o 'resend'"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    sort_by: str = Query("at", description="at | email | subject | origin | status"),
    sort_dir: str = Query("desc", description="asc | desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    sort_col = _SORT_COLUMNS.get(sort_by, "at")
    sort_direction = "ASC" if sort_dir == "asc" else "DESC"

    # Counts (ses/resend/total) ignore the provider filter on purpose — see
    # module docstring — so they reflect the other active filters only.
    counts_where, counts_params = _build_where(
        email=email, subject=subject, origin=origin, status=status,
        date_from=date_from, date_to=date_to, include_provider=False, provider=None,
    )
    counts_where_sql = f"WHERE {' AND '.join(counts_where)}" if counts_where else ""
    counts_query = text(f"""
        {_UNIFIED_CTE}
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE LENGTH(resend_id) >= {_SES_ID_MIN_LEN}) AS ses_count,
            COUNT(*) FILTER (WHERE resend_id IS NOT NULL AND LENGTH(resend_id) < {_SES_ID_MIN_LEN}) AS resend_count
        FROM unified
        {counts_where_sql}
    """)
    counts_row = session.connection().execute(counts_query, counts_params).one()

    # Page of rows — same filters plus provider, with the requested sort.
    page_where, page_params = _build_where(
        email=email, subject=subject, origin=origin, status=status,
        date_from=date_from, date_to=date_to, include_provider=True, provider=provider,
    )
    page_where_sql = f"WHERE {' AND '.join(page_where)}" if page_where else ""
    page_params["skip"] = skip
    page_params["limit"] = limit

    page_query = text(f"""
        {_UNIFIED_CTE}
        SELECT
            row_id, source_type, source_name, email, at, subject, status,
            CASE WHEN LENGTH(resend_id) >= {_SES_ID_MIN_LEN} THEN 'ses' ELSE 'resend' END AS provider
        FROM unified
        {page_where_sql}
        ORDER BY {sort_col} {sort_direction} NULLS LAST, source_type, row_id
        LIMIT :limit OFFSET :skip
    """)
    rows = session.connection().execute(page_query, page_params).fetchall()

    items = [
        SentEmailRow(
            id=r.row_id, source_type=r.source_type, source_name=r.source_name,
            email=r.email, at=r.at, subject=r.subject, status=r.status, provider=r.provider,
        )
        for r in rows
    ]
    # total for pagination reflects the provider filter too (matches what's shown).
    total = counts_row.ses_count if provider == "ses" else counts_row.resend_count if provider == "resend" else counts_row.total
    return SentEmailsPage(
        items=items, total=total,
        ses_count=counts_row.ses_count, resend_count=counts_row.resend_count,
    )


class SentEmailDetail(BaseModel):
    subject: str
    html: Optional[str] = None
    # False for sends made before html_content started being stored — the
    # frontend shows "no disponible" instead of a blank preview.
    available: bool


_DETAIL_QUERIES = {
    "campaign": """
        SELECT COALESCE(cs.rendered_subject, c.subject) AS subject, cs.html_content
        FROM campaign_sends cs JOIN campaigns c ON c.id = cs.campaign_id
        WHERE cs.id = :id
    """,
    "automation": """
        SELECT COALESCE(ar.rendered_subject, a.subject) AS subject, ar.html_content
        FROM automation_runs ar JOIN automations a ON a.id = ar.automation_id
        WHERE ar.id = :id
    """,
    "other": "SELECT subject, html_content FROM email_log WHERE id = :id",
}


@router.get("/{source_type}/{row_id}", response_model=SentEmailDetail)
def get_sent_email_detail(
    source_type: str,
    row_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    query = _DETAIL_QUERIES.get(source_type)
    if not query:
        raise HTTPException(status_code=400, detail="source_type inválido")

    row = session.connection().execute(text(query), {"id": row_id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="No encontrado")

    return SentEmailDetail(subject=row.subject, html=row.html_content, available=row.html_content is not None)
