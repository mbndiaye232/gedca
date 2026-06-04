"""Modèles SQLAlchemy.

Chaque module métier importe ses modèles depuis ici pour Alembic puisse
les détecter via `Base.metadata`.
"""

from app.models.agent import Agent, Departement, Role, TypeCorrespondant
from app.models.audit import AuditLog
from app.models.tenant import Tenant

__all__ = [
    "Agent",
    "AuditLog",
    "Departement",
    "Role",
    "Tenant",
    "TypeCorrespondant",
]
