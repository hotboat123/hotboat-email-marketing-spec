from typing import Optional, Any
from datetime import datetime
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON


class Automation(SQLModel, table=True):
    __tablename__ = "automations"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    # abandoned_booking | welcome | post_visit | reactivation | tc_signature | birthday
    trigger_type: str
    trigger_config: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    template_id: int = Field(foreign_key="templates.id")
    subject: str
    # active | paused
    status: str = Field(default="active")
    # "Modo test" — cuando está prendido, cada envío real también le llega en
    # copia (BCC) a NOTIFY_EMAIL, al mismo tiempo que al cliente. Por
    # automatización, no global.
    bcc_admin: bool = Field(default=False)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AutomationRun(SQLModel, table=True):
    __tablename__ = "automation_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    automation_id: int = Field(foreign_key="automations.id", index=True)
    contact_id: Optional[int] = Field(default=None, foreign_key="contacts.id", index=True)
    contact_email: str
    # Unique string per trigger event — prevents double-send
    trigger_key: str = Field(index=True)
    # sent | failed | skipped
    status: str = Field(default="sent")
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    executed_at: Optional[datetime] = None
    resend_id: Optional[str] = Field(default=None, index=True)
    error: Optional[str] = None
    # Filled in by the same Resend webhook (app/routers/webhooks.py) that
    # already updates CampaignSend — matched by resend_id, same event types
    # (email.delivered/opened/clicked/bounced). Null until Resend reports it.
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    # Snapshot of the extra_vars an email was sent with — lets a later step in
    # a sequence (e.g. abandoned-cart follow-up) reuse them once the source
    # row they came from (all_appointments) is gone.
    extra_data: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    # Subject/HTML actually rendered and sent for this run (post-Jinja,
    # post-[OVERRIDE] prefix if applicable) — automations.subject is the raw
    # template with {{ nombre }} unrendered, so "Correos enviados" needs
    # these to show exactly what went out, not just metadata.
    rendered_subject: Optional[str] = None
    html_content: Optional[str] = None


class AutomationCreate(SQLModel):
    name: str
    trigger_type: str
    trigger_config: Optional[dict] = None
    template_id: int
    subject: str


class AutomationUpdate(SQLModel):
    name: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict] = None
    template_id: Optional[int] = None
    subject: Optional[str] = None
    status: Optional[str] = None
    bcc_admin: Optional[bool] = None


class AutomationRead(SQLModel):
    id: int
    name: str
    trigger_type: str
    trigger_config: Optional[dict]
    template_id: int
    subject: str
    status: str
    bcc_admin: bool = False
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime


class AutomationRunRead(SQLModel):
    id: int
    automation_id: int
    contact_id: Optional[int]
    contact_email: str
    trigger_key: str
    status: str
    triggered_at: datetime
    executed_at: Optional[datetime]
    resend_id: Optional[str]
    error: Optional[str]
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
