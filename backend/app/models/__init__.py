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
from app.models.courrier import (
    ActionCourrier,
    CopieCourrier,
    Courrier,
    DocumentCourrier,
    HistoriqueCourrier,
    Imputation,
    NoteCourrier,
    StatutCourrier,
)
from app.models.document import Document, DocumentVersion
from app.models.referentiel import Categorie, Thematique, TypeDocument
from app.models.tenant import Tenant

__all__ = [
    "ActionCourrier",
    "Agent",
    "AuditLog",
    "Boite",
    "Categorie",
    "CopieCourrier",
    "Correspondant",
    "Courrier",
    "Departement",
    "Document",
    "DocumentCourrier",
    "DocumentSousDossier",
    "DocumentVersion",
    "DossierClasseur",
    "HistoriqueCourrier",
    "Imputation",
    "LocalSalle",
    "NoteCourrier",
    "Rayon",
    "Role",
    "Site",
    "SousDossier",
    "StatutCourrier",
    "Tenant",
    "Thematique",
    "TypeCorrespondant",
    "TypeDocument",
]
