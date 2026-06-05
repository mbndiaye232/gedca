"""Routes versionnées API v1."""

from fastapi import APIRouter

from app.api.v1 import agents, audit_log, auth, departements, structure

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(departements.router)
api_router.include_router(structure.router)
api_router.include_router(audit_log.router)
