"""Service Redirection — résolution du destinataire effectif d'un courrier.

Quand un agent A est absent et a créé une redirection vers B, tout courrier
qui aurait dû être attribué à A est automatiquement réorienté vers B :
- `agent_proprietaire_id` = B (le substitut traite)
- `agent_destinataire_id` reste A (info traçable : c'est lui le destinataire
  fonctionnel, le substitut n'est qu'un proxy)
- Une ligne d'historique avec action `redirection` est ajoutée pour tracer.

Règle non-rétroactive (PDF p. 1) : les courriers déjà en cours de traitement
chez A avant la création de la redirection ne sont PAS déplacés. C'est pour
ça que ce service ne touche QUE le flux d'écriture (création, imputation,
réponse), pas les courriers existants.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Redirection


@dataclass(frozen=True, slots=True)
class ResultatRedirection:
    """Sortie de `resoudre_destinataire_effectif`."""

    agent_effectif_id: int
    """L'agent qui doit recevoir le courrier en pratique (peut être le
    substitut si redirection active, sinon le destinataire d'origine)."""

    redirection: Redirection | None
    """L'objet Redirection appliqué, ou None si aucune redirection active."""

    @property
    def a_redirige(self) -> bool:
        return self.redirection is not None


async def resoudre_destinataire_effectif(
    db: AsyncSession, *, agent_destinataire_id: int, tenant_id: int
) -> ResultatRedirection:
    """Renvoie le destinataire effectif d'un courrier.

    Si l'agent destinataire a une redirection active, retourne le
    substitut + l'objet redirection. Sinon retourne l'agent destinataire
    inchangé.
    """
    redirection = await db.scalar(
        select(Redirection).where(
            Redirection.tenant_id == tenant_id,
            Redirection.agent_redirige_id == agent_destinataire_id,
            Redirection.active.is_(True),
        )
    )
    if redirection is None:
        return ResultatRedirection(
            agent_effectif_id=agent_destinataire_id, redirection=None
        )
    return ResultatRedirection(
        agent_effectif_id=redirection.agent_substitut_id,
        redirection=redirection,
    )
