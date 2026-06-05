"""Modèle Correspondant — personne physique ou morale externe.

Aligne avec `correspondants` de la base d'origine (`docs/dumpbdsoftged.txt`) :
`nomrs`, `societe`, `titre`, `tel`, `cel`, `fax`, `adr`, `email`.

Le champ `civilite` (`titre` dans l'origine) est utilisé pour personne physique.
Le champ `societe` (entreprise d'affiliation) est conservé même pour personne
physique — utile pour identifier qui parle au nom de qui.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.agent import TypeCorrespondant
    from app.models.tenant import Tenant


class Correspondant(Base):
    """Correspondant externe (expéditeur/destinataire de courriers)."""

    __tablename__ = "correspondants"
    __table_args__ = (
        # Personne morale → raison sociale obligatoire ; personne physique → nom obligatoire.
        CheckConstraint(
            "(type_id = 1 AND raison_sociale IS NOT NULL) OR "
            "(type_id = 2 AND nom IS NOT NULL)",
            name="ck_correspondants_identification",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    type_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("types_correspondant.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Personne morale
    raison_sociale: Mapped[str | None] = mapped_column(String(255))

    # Personne physique
    civilite: Mapped[str | None] = mapped_column(String(16))
    nom: Mapped[str | None] = mapped_column(String(128))
    prenom: Mapped[str | None] = mapped_column(String(128))

    # Société d'affiliation (utile pour personne physique parlant au nom d'une organisation)
    societe: Mapped[str | None] = mapped_column(String(255))

    # Coordonnées
    fonction: Mapped[str | None] = mapped_column(String(128))
    adresse: Mapped[str | None] = mapped_column(Text)
    telephone: Mapped[str | None] = mapped_column(String(64))
    cellulaire: Mapped[str | None] = mapped_column(String(64))
    fax: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(255))

    notes: Mapped[str | None] = mapped_column(Text)
    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    type_correspondant: Mapped[TypeCorrespondant] = relationship(lazy="joined")

    @property
    def libelle_affichage(self) -> str:
        """Texte court pour les listes : raison sociale ou prénom+nom."""
        if self.raison_sociale:
            return self.raison_sociale
        parts = [self.civilite, self.prenom, self.nom]
        return " ".join(p for p in parts if p)

    def __repr__(self) -> str:
        return f"<Correspondant id={self.id} libelle={self.libelle_affichage!r}>"
