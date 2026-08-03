"""
Unified sent-email log — combines campaign sends and automation runs into
a single, filterable, paginated view (mirrors the "Correos enviados" page
from the sibling Happy Lápiz product). A raw SQL UNION ALL over both tables
(rather than two ORM queries merged in Python) is what makes global sorting
+ pagination across ~15k+ rows correct and cheap — Postgres does the work,
not this process.

`provider` (SES vs Resend) isn't a stored column on either table — adding
one would need a migration and can't be back-filled for historical rows
anyway. Instead it's derived from resend_id length: Resend's ids are
always a 36-char UUID; SES's (sesv2) are much longer
(hex-hyphen-uuid-hyphen-seq, ~59-70 chars). Good enough to answer "how much
do I owe for SES" without a schema change.
"""
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
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
        ct.email AS email,
        cs.sent_at AS at,
        c.subject AS subject,
        cs.status AS status,
        cs.resend_id AS resend_id
    FROM campaign_sends cs
    JOIN campaigns c ON c.id = cs.campaign_id
    JOIN contacts ct ON ct.id = cs.contact_id
    WHERE cs.sent_at IS NOT NULL

    UNION ALL

    SELECT
        ar.id AS row_id,
        'automation' AS source_type,
        a.name AS source_name,
        ar.contact_email AS email,
        ar.triggered_at AS at,
        a.subject AS subject,
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
)
"""


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


@router.get("", response_model=SentEmailsPage)
def list_sent_emails(
    email: Optional[str] = Query(None, description="Búsqueda parcial en el email del destinatario"),
    subject: Optional[str] = Query(None, description="Búsqueda parcial en el asunto"),
    origin: Optional[str] = Query(None, description="'campaign' o 'automation'"),
    status: Optional[str] = Query(None),
    provider: Optional[str] = Query(None, description="'ses' o 'resend'"),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    where = []
    params: dict = {"skip": skip, "limit": limit}

    if email:
        where.append("email ILIKE :email")
        params["email"] = f"%{email}%"
    if subject:
        where.append("subject ILIKE :subject")
        params["subject"] = f"%{subject}%"
    if origin in ("campaign", "automation"):
        where.append("source_type = :origin")
        params["origin"] = origin
    if status:
        where.append("status = :status")
        params["status"] = status
    if provider in ("ses", "resend"):
        if provider == "ses":
            where.append(f"LENGTH(resend_id) >= {_SES_ID_MIN_LEN}")
        else:
            where.append(f"(resend_id IS NOT NULL AND LENGTH(resend_id) < {_SES_ID_MIN_LEN})")
    if date_from:
        where.append("at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where.append("at < :date_to_excl")
        params["date_to_excl"] = date_to + timedelta(days=1)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    query = text(f"""
        {_UNIFIED_CTE}
        SELECT
            row_id, source_type, source_name, email, at, subject, status,
            CASE WHEN LENGTH(resend_id) >= {_SES_ID_MIN_LEN} THEN 'ses' ELSE 'resend' END AS provider,
            COUNT(*) OVER() AS total_count
        FROM unified
        {where_sql}
        ORDER BY at DESC
        LIMIT :limit OFFSET :skip
    """)
    result = session.connection().execute(query, params)
    rows = result.fetchall()

    total = rows[0].total_count if rows else 0
    items = [
        SentEmailRow(
            id=r.row_id, source_type=r.source_type, source_name=r.source_name,
            email=r.email, at=r.at, subject=r.subject, status=r.status, provider=r.provider,
        )
        for r in rows
    ]
    return SentEmailsPage(items=items, total=total)
