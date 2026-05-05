from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import create_db_and_tables
from app.routers import auth, contacts, segments, templates, campaigns, webhooks, analytics, sync

app = FastAPI(title="HotBoat Email Marketing API", version="1.0.0", redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(segments.router, prefix="/api/segments", tags=["segments"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(sync.router, prefix="/api/sync", tags=["sync"])


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/api/health")
def health():
    return {"status": "ok"}
