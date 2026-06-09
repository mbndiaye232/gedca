"""Job quotidien d'envoi des alertes de retard sur les courriers.

Stratégie
- Pour chaque courrier ouvert (statut a_traiter | a_faire_valider |
  en_validation) avec `date_limite IS NOT NULL`, on calcule
  `jours_restants = date_limite - today()`.
- Si `jours_restants` est dans `PALIERS = (5, 3, 2, 1, 0)` et que
  l'alerte n'a pas déjà été envoyée pour ce palier + courrier + agent,
  on envoie un mail.
- Destinataires : propriétaire actuel + agents en copie + valideur
  désigné le cas échéant (PRD-06B).
- Anti-doublon : table `alertes_retard_envoyees` avec contrainte
  unique sur (courrier_id, agent_id, palier).

Le job est lancé via Celery beat (cron quotidien à 07:00 UTC).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import async_session_factory
from app.models import AlerteRetardEnvoyee, CopieCourrier, Courrier
from app.services.notifications import notifier_alerte_retard

logger = logging.getLogger(__name__)

# Statuts qui restent "ouverts" (le travail n'est pas terminé donc la
# date limite est encore pertinente). Aligné avec la définition de la
# corbeille « En retard » côté courriers.py.
STATUTS_OUVERTS = (1, 3, 4)  # a_traiter, a_faire_valider, en_validation

PALIERS = (5, 3, 2, 1, 0)


async def envoyer_alertes_quotidiennes() -> dict[str, int]:
    """Scan + envoi des alertes pour aujourd'hui.

    Retourne un compteur par palier (utile pour le log et les tests
    futurs).
    """
    today = date.today()
    # Pour chaque palier, calcule la date_limite correspondante et
    # interroge la DB. On groupe les requêtes par palier pour minimiser
    # le nombre d'allers-retours.
    stats = {f"j{p}": 0 for p in PALIERS}
    stats["skipped_doublon"] = 0
    stats["sans_email"] = 0

    async with async_session_factory() as db:
        for palier in PALIERS:
            cible = today + timedelta(days=palier)

            # Courriers à alerter pour ce palier
            res = await db.execute(
                select(Courrier).where(
                    Courrier.supprime.is_(False),
                    Courrier.statut_id.in_(STATUTS_OUVERTS),
                    Courrier.date_limite == cible,
                )
            )
            courriers = list(res.scalars())

            for courrier in courriers:
                # Récupère le bouquet de destinataires : propriétaire +
                # agents en copie + valideur le cas échéant.
                destinataires: set[int] = {courrier.agent_proprietaire_id}
                if courrier.agent_valideur_id is not None:
                    destinataires.add(courrier.agent_valideur_id)
                res_copies = await db.execute(
                    select(CopieCourrier.agent_id).where(
                        CopieCourrier.courrier_id == courrier.id
                    )
                )
                destinataires.update(int(x) for x in res_copies.scalars())

                for agent_id in destinataires:
                    # Anti-doublon : insertion conditionnelle.
                    # ON CONFLICT DO NOTHING → on saute si l'alerte
                    # existe déjà pour ce trio.
                    stmt = pg_insert(AlerteRetardEnvoyee).values(
                        courrier_id=courrier.id,
                        agent_id=agent_id,
                        palier=palier,
                    ).on_conflict_do_nothing(
                        constraint="uq_alertes_retard_unique"
                    ).returning(AlerteRetardEnvoyee.id)
                    res_ins = await db.execute(stmt)
                    inserted_id = res_ins.scalar_one_or_none()
                    if inserted_id is None:
                        stats["skipped_doublon"] += 1
                        continue

                    # Une ligne a été insérée → on commit + envoie le mail
                    await db.commit()
                    await notifier_alerte_retard(
                        courrier_id=courrier.id,
                        agent_id=agent_id,
                        palier=palier,
                        tenant_id=courrier.tenant_id,
                    )
                    stats[f"j{palier}"] += 1

    logger.info("Alertes retard quotidiennes : %s", stats)
    return stats
