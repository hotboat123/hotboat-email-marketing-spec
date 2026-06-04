from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


class BrandAsset(SQLModel, table=True):
    __tablename__ = "brand_assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    categoria: str = Field(index=True)   # color | tipografia | logo | url | espaciado
    nombre: str
    valor: str                           # hex, font name, URL, px value...
    descripcion: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BrandAssetCreate(SQLModel):
    categoria: str
    nombre: str
    valor: str
    descripcion: Optional[str] = None


class BrandAssetUpdate(SQLModel):
    categoria: Optional[str] = None
    nombre: Optional[str] = None
    valor: Optional[str] = None
    descripcion: Optional[str] = None


class BrandAssetRead(SQLModel):
    id: int
    categoria: str
    nombre: str
    valor: str
    descripcion: Optional[str]
    created_at: datetime
    updated_at: datetime
