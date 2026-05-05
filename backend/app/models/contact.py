from typing import Optional, List
from datetime import datetime, date
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String, Text


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
    veces_hotboat: int
    ultima_visita: Optional[date]
    ha_alojamiento: bool
    extras_favoritos: Optional[List[str]]
    ticket_medio: Optional[float]
    created_at: datetime
    updated_at: datetime
