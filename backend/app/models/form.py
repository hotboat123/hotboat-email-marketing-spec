from typing import Optional, Any
from datetime import datetime
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON, Text


class SignupForm(SQLModel, table=True):
    __tablename__ = "signup_forms"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    title: str
    description: Optional[str] = None
    button_text: str = Field(default="Suscribirme")
    success_message: str = Field(default="¡Gracias! Pronto recibirás noticias nuestras.")
    collect_name: bool = Field(default=True)
    collect_phone: bool = Field(default=False)
    # delay | exit_intent | scroll
    popup_trigger: str = Field(default="delay")
    popup_delay_seconds: int = Field(default=5)
    popup_scroll_pct: int = Field(default=50)
    # Custom fields: list of {key, label, type, required, placeholder, options}
    custom_form_fields: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    # Full HTML override for popup content (null = use auto-generated)
    html_override: Optional[str] = Field(default=None, sa_column=Column(Text))
    # active | paused
    status: str = Field(default="active")
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FormSubmission(SQLModel, table=True):
    __tablename__ = "form_submissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    form_id: int = Field(foreign_key="signup_forms.id", index=True)
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    source_url: Optional[str] = None
    extra_data: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SignupFormCreate(SQLModel):
    name: str
    title: str
    description: Optional[str] = None
    button_text: str = "Suscribirme"
    success_message: str = "¡Gracias! Pronto recibirás noticias nuestras."
    collect_name: bool = True
    collect_phone: bool = False
    popup_trigger: str = "delay"
    popup_delay_seconds: int = 5
    popup_scroll_pct: int = 50
    custom_form_fields: Optional[list] = None
    html_override: Optional[str] = None


class SignupFormUpdate(SQLModel):
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    button_text: Optional[str] = None
    success_message: Optional[str] = None
    collect_name: Optional[bool] = None
    collect_phone: Optional[bool] = None
    popup_trigger: Optional[str] = None
    popup_delay_seconds: Optional[int] = None
    popup_scroll_pct: Optional[int] = None
    custom_form_fields: Optional[list] = None
    html_override: Optional[str] = None
    status: Optional[str] = None


class SignupFormRead(SQLModel):
    id: int
    name: str
    title: str
    description: Optional[str]
    button_text: str
    success_message: str
    collect_name: bool
    collect_phone: bool
    popup_trigger: str
    popup_delay_seconds: int
    popup_scroll_pct: int
    custom_form_fields: Optional[list]
    html_override: Optional[str]
    status: str
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime


class FormSubmitPayload(SQLModel):
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    source_url: Optional[str] = None
    extra_data: Optional[dict] = None
