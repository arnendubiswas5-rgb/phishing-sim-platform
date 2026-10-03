from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.short_links import router as short_links_router
from app.api.tracking import router as tracking_router
from app.api.training_public import router as training_public_router
from app.api.v1 import api_router
from app.config import settings
from app.middleware.audit import AuditLogMiddleware
from app.seed import seed_default_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_default_admin()
    yield


app = FastAPI(title="Phishing Simulation Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Records successful create/update/delete calls to /api/v1 in audit_logs.
app.add_middleware(AuditLogMiddleware)

app.include_router(api_router)
# Deliberately not under api_router / /api/v1 - these are short, public,
# unauthenticated links embedded directly in campaign emails.
app.include_router(tracking_router)
# Short-code redirector (/s/{code}) that resolves to the real tracking URL.
app.include_router(short_links_router)
# Public, unauthenticated training pages at /training/{assignment_id}.
app.include_router(training_public_router)


@app.get("/health")
def health():
    return {"status": "ok"}
