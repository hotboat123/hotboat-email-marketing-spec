from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


class EmailLog(SQLModel, table=True):
    """Catch-all record of every send_email() call whose trigger isn't
    already tracked via CampaignSend/AutomationRun (see _TRACKED_ELSEWHERE
    in app/email/send_email.py) — e.g. unsubscribe notices, internal admin
    alerts, or any future call site that forgets to add its own tracking
    row. Written unconditionally inside the funnel itself so "Correos
    enviados" can never silently miss a real SES/Resend send again."""
    __tablename__ = "email_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    to_email: str
    subject: str
    html_content: str
    provider: Optional[str] = None
    message_id: Optional[str] = Field(default=None, index=True)
    sent: bool = Field(default=False)
    error: Optional[str] = None
    trigger: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
