from fastapi import APIRouter

from app.api.v1 import (
    audit,
    auth,
    campaigns,
    pages,
    reports,
    settings,
    smtp,
    targets,
    templates,
    training_modules,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(targets.router)
api_router.include_router(templates.router)
api_router.include_router(pages.router)
api_router.include_router(smtp.router)
api_router.include_router(campaigns.router)
api_router.include_router(reports.router)
api_router.include_router(training_modules.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)

# Public tracking-link endpoints (pixel/click/submit/education) live under
# app.api.tracking instead, mounted directly on the app in main.py without
# the /api/v1 prefix - see that module.
