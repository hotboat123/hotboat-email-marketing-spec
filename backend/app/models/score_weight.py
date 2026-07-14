from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


class ScoreWeight(SQLModel, table=True):
    """Puntos configurables de _compute_score() (app/services/crm_sync.py), editables
    desde el dashboard (Llamadas > Configuración) sin tocar código. Si la tabla esta
    vacia, crm_sync usa los defaults hardcodeados en SCORE_WEIGHTS."""
    __tablename__ = "score_weights"

    key: str = Field(primary_key=True)  # debe matchear una clave de crm_sync.SCORE_WEIGHTS
    label: str
    points: int
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ScoreWeightRead(SQLModel):
    key: str
    label: str
    points: int
    updated_at: datetime


class ScoreWeightUpdate(SQLModel):
    key: str
    points: int
