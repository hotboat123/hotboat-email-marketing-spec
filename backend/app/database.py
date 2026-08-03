from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    # Bumped from 5+10: the campaigns list page alone used to fire 2 requests
    # PER campaign (stats + conversions) concurrently — with 70+ campaigns
    # that exhausted the old pool outright (QueuePool timeout, 500s) even
    # though Postgres itself had plenty of headroom (max_connections=100,
    # ~30 in use). The real fix is campaigns_bulk_metrics() replacing that
    # N+1 pattern; this is a safety margin for whatever else fans out.
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
