from typing import Optional, List, Any
from datetime import datetime, date
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy import String, Text


class ContactCRM(SQLModel, table=True):
    """Unified CRM record — covers every WhatsApp lead / booking customer,
    with or without email. Independent from `contacts` (the email-subscriber
    list owned by the rest of this app): never written to, never altered.
    `linked_contact_id` is a soft, read-only pointer to `contacts.id` when the
    same email exists there — no FK constraint, so this table's lifecycle
    never depends on `contacts`.
    """
    __tablename__ = "contacts_crm"

    id: Optional[int] = Field(default=None, primary_key=True)
    phone: Optional[str] = Field(default=None, index=True, unique=True)  # E.164
    email: Optional[str] = None
    name: Optional[str] = None

    linked_contact_id: Optional[int] = None  # contacts.id, soft reference only

    # Atribución de anuncio
    ad_source: Optional[str] = None
    ad_platform: Optional[str] = None
    ad_creative_url: Optional[str] = None
    utm_campaign: Optional[str] = None

    lead_status: Optional[str] = None
    last_interaction_at: Optional[datetime] = None  # ultimo mensaje de WhatsApp (whatsapp_leads)

    # Historial de reservas
    veces_hotboat: int = Field(default=0)
    ultima_visita: Optional[date] = None
    ticket_medio: Optional[float] = None
    extras_favoritos: Optional[List[str]] = Field(
        default=None, sa_column=Column(ARRAY(String))
    )

    # Score de probabilidad de reserva
    reservation_score: Optional[int] = None
    score_updated_at: Optional[datetime] = None
    score_breakdown: Optional[Any] = Field(default=None, sa_column=Column(JSONB))

    # Cola de llamadas
    call_status: str = Field(default="pending")
    call_status_updated_at: Optional[datetime] = None

    # Seguimiento del link de cotización enviado por WhatsApp (tracked_quote_links
    # en hotboat-whatsapp) — solo cubre leads a los que el bot les mandó ese link.
    link_clicked: bool = Field(default=False)
    link_viewed_prices: bool = Field(default=False)
    link_selected_date: bool = Field(default=False)
    link_last_seen_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContactCRMRead(SQLModel):
    id: int
    phone: Optional[str]
    email: Optional[str]
    name: Optional[str]
    linked_contact_id: Optional[int]
    ad_source: Optional[str]
    ad_platform: Optional[str]
    ad_creative_url: Optional[str]
    utm_campaign: Optional[str]
    lead_status: Optional[str]
    last_interaction_at: Optional[datetime]
    veces_hotboat: int
    ultima_visita: Optional[date]
    ticket_medio: Optional[float]
    extras_favoritos: Optional[List[str]]
    reservation_score: Optional[int]
    score_updated_at: Optional[datetime]
    score_breakdown: Optional[dict]
    call_status: str
    call_status_updated_at: Optional[datetime]
    link_clicked: bool
    link_viewed_prices: bool
    link_selected_date: bool
    link_last_seen_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class CallStatusUpdate(SQLModel):
    call_status: str
    note: Optional[str] = None
    created_by: Optional[str] = None
