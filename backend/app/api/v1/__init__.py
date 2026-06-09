"""Routes versionnées API v1."""

from fastapi import APIRouter

from app.api.v1 import (
    agents,
    archivage,
    audit_log,
    auth,
    correspondants,
    courriers,
    departements,
    documents,
    redirections,
    referentiels,
    structure,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(departements.router)
api_router.include_router(structure.router)
api_router.include_router(audit_log.router)
api_router.include_router(documents.router)
api_router.include_router(referentiels.router)
api_router.include_router(archivage.router)
api_router.include_router(correspondants.router)
api_router.include_router(courriers.router)
api_router.include_router(redirections.router)
