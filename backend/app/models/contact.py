from typing import Optional, List, Any
from datetime import datetime, date
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String, Text, JSON
from pydantic import field_validator


class Contact(SQLModel, table=True):
    __tablename__ = "contacts"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None          # es | en
    origin_utm: Optional[str] = None        # fuente del lead

    # opt-in
    opted_in: bool = Field(default=True)
    opted_in_at: Optional[datetime] = None
    opted_out_at: Optional[datetime] = None

    # atributos HotBoat
    veces_hotboat: int = Field(default=0)
    ultima_visita: Optional[date] = None
    ha_alojamiento: bool = Field(default=False)
    extras_favoritos: Optional[List[str]] = Field(
        default=None, sa_column=Column(ARRAY(String))
    )
    ticket_medio: Optional[float] = None

    # perfil ampliado
    birthday: Optional[date] = None
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    custom_fields: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContactCreate(SQLModel):
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None
    origin_utm: Optional[str] = None
    opted_in: bool = True
    veces_hotboat: int = 0
    ultima_visita: Optional[date] = None
    ha_alojamiento: bool = False
    extras_favoritos: Optional[List[str]] = None
    ticket_medio: Optional[float] = None
    birthday: Optional[date] = None
    notes: Optional[str] = None
    custom_fields: Optional[dict] = None


class ContactUpdate(SQLModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None
    origin_utm: Optional[str] = None
    opted_in: Optional[bool] = None
    veces_hotboat: Optional[int] = None
    ultima_visita: Optional[date] = None
    ha_alojamiento: Optional[bool] = None
    extras_favoritos: Optional[List[str]] = None
    ticket_medio: Optional[float] = None
    birthday: Optional[date] = None
    notes: Optional[str] = None
    custom_fields: Optional[dict] = None


class ContactRead(SQLModel):
    id: int
    email: str
    name: Optional[str]
    phone: Optional[str]
    language: Optional[str]
    origin_utm: Optional[str]
    opted_in: bool
    opted_in_at: Optional[datetime]
    opted_out_at: Optional[datetime]
    veces_hotboat: int = 0
    ultima_visita: Optional[date] = None
    ha_alojamiento: bool = False
    extras_favoritos: Optional[List[str]] = None
    ticket_medio: Optional[float] = None
    birthday: Optional[date] = None
    notes: Optional[str] = None
    custom_fields: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("veces_hotboat", mode="before")
    @classmethod
    def _coerce_veces(cls, v: object) -> int:
        return int(v) if v is not None else 0

    @field_validator("ha_alojamiento", mode="before")
    @classmethod
    def _coerce_alojamiento(cls, v: object) -> bool:
        return bool(v) if v is not None else False
