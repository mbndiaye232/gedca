"""Modèles SQLAlchemy.

Chaque module métier importe ses modèles depuis ici pour Alembic puisse
les détecter via `Base.metadata`.
"""

from app.models.agent import Agent, Departement, Role, TypeCorrespondant
from app.models.archivage import (
    Boite,
    DocumentSousDossier,
    DossierClasseur,
    LocalSalle,
    Rayon,
    Site,
    SousDossier,
)
from app.models.audit import AuditLog
from app.models.correspondant import Correspondant
from app.models.document import Document, DocumentVersion
from app.models.referentiel import Categorie, Thematique, TypeDocument
from app.models.tenant import Tenant

__all__ = [
    "Agent",
    "AuditLog",
    "Boite",
    "Categorie",
    "Correspondant",
    "Departement",
    "Document",
    "DocumentSousDossier",
    "DocumentVersion",
    "DossierClasseur",
    "LocalSalle",
    "Rayon",
    "Role",
    "Site",
    "SousDossier",
    "Tenant",
    "Thematique",
    "TypeCorrespondant",
    "TypeDocument",
]
