from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


class CallActivity(SQLModel, table=True):
    """History of call_status changes on a ContactCRM row (one row per change)."""
    __tablename__ = "call_activity"

    id: Optional[int] = Field(default=None, primary_key=True)
    contact_crm_id: int = Field(foreign_key="contacts_crm.id", index=True)
    old_status: Optional[str] = None
    new_status: str
    note: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CallActivityRead(SQLModel):
    id: int
    contact_crm_id: int
    old_status: Optional[str]
    new_status: str
    note: Optional[str]
    created_by: Optional[str]
    created_at: datetime
