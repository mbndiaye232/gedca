"""Routes Statistiques d'activité — réservées au superviseur.

- GET /api/statistiques/activite-agents : compteurs par agent sur une période.

L'approche
- On agrège la table `historiques_courrier` par (agent_id, action_id)
  sur la fenêtre [date_debut, date_fin + 1 jour[.
- On joint la table `agents` pour récupérer prénom/nom/fonction/département.
- Pour les compteurs "à traiter" et "en retard", on s'appuie sur l'état
  CURRENT des courriers (statut + agent_proprietaire_id + date_limite).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, case, func, select

from app.api.deps import AgentSuperviseur, SessionDB
from app.models import Agent, Courrier, Departement, HistoriqueCourrier
from app.schemas.statistiques import (
    StatistiquesActiviteAgent,
    StatistiquesActiviteReponse,
)

router = APIRouter(prefix="/statistiques", tags=["statistiques"])

# Codes d'action (cf. migrations 005 + 006 + 007)
ACTION_CREATION = 1
ACTION_COPIE = 2
ACTION_IMPUTATION = 3
ACTION_REPONSE = 4
ACTION_ENVOI = 5
ACTION_NOTE = 6
ACTION_AJOUT_DOCUMENT = 7
ACTION_DEMANDE_VALIDATION = 8
ACTION_VALIDATION = 9

STATUT_A_TRAITER = 1
STATUT_A_FAIRE_VALIDER = 3
STATUT_EN_VALIDATION = 4
STATUTS_OUVERTS = (STATUT_A_TRAITER, STATUT_A_FAIRE_VALIDER, STATUT_EN_VALIDATION)


@router.get(
    "/activite-agents",
    response_model=StatistiquesActiviteReponse,
    summary="Activité des agents sur une période (superviseur)",
)
async def activite_agents(
    superviseur: AgentSuperviseur,
    db: SessionDB,
    date_debut: date | None = Query(
        None, description="Début de période (incluse). Défaut : début d'exploitation."
    ),
    date_fin: date | None = Query(
        None, description="Fin de période (incluse). Défaut : aujourd'hui."
    ),
) -> StatistiquesActiviteReponse:
    """Compte les actions effectuées par chaque agent sur la période donnée."""
    aujourd_hui = date.today()
    if date_fin is None:
        date_fin = aujourd_hui

    # Détermine le début d'exploitation si non fourni : date du premier
    # courrier créé dans le tenant.
    if date_debut is None:
        res = await db.scalar(
            select(func.min(Courrier.created_at)).where(
                Courrier.tenant_id == superviseur.tenant_id
            )
        )
        if res is not None:
            date_debut = res.date() if hasattr(res, "date") else res
        else:
            date_debut = date_fin

    if date_debut > date_fin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La date de début doit être antérieure ou égale à la date de fin.",
        )

    debut_dt = datetime.combine(date_debut, time.min, tzinfo=timezone.utc)
    fin_dt = datetime.combine(
        date_fin + timedelta(days=1), time.min, tzinfo=timezone.utc
    )

    # ----------------------------------------------------------------
    # 1) Agrégation par agent_id et action_id
    # ----------------------------------------------------------------
    res_actions = await db.execute(
        select(
            HistoriqueCourrier.agent_id,
            HistoriqueCourrier.action_id,
            func.count(HistoriqueCourrier.id).label("nb"),
        )
        .join(Courrier, Courrier.id == HistoriqueCourrier.courrier_id)
        .where(
            Courrier.tenant_id == superviseur.tenant_id,
            Courrier.supprime.is_(False),
            HistoriqueCourrier.ts >= debut_dt,
            HistoriqueCourrier.ts < fin_dt,
            HistoriqueCourrier.agent_id.is_not(None),
        )
        .group_by(HistoriqueCourrier.agent_id, HistoriqueCourrier.action_id)
    )
    compteurs: dict[int, dict[int, int]] = {}
    for agent_id, action_id, nb in res_actions:
        compteurs.setdefault(agent_id, {})[action_id] = nb

    # ----------------------------------------------------------------
    # 2) Charge actuelle : courriers à traiter et en retard
    # ----------------------------------------------------------------
    res_charge = await db.execute(
        select(
            Courrier.agent_proprietaire_id.label("agent_id"),
            func.count(Courrier.id).label("a_traiter"),
            func.sum(
                case(
                    (
                        and_(
                            Courrier.date_limite.is_not(None),
                            Courrier.date_limite < aujourd_hui,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("en_retard"),
        )
        .where(
            Courrier.tenant_id == superviseur.tenant_id,
            Courrier.supprime.is_(False),
            Courrier.statut_id.in_(STATUTS_OUVERTS),
        )
        .group_by(Courrier.agent_proprietaire_id)
    )
    charge: dict[int, tuple[int, int]] = {
        row.agent_id: (int(row.a_traiter or 0), int(row.en_retard or 0))
        for row in res_charge
    }

    # ----------------------------------------------------------------
    # 3) Liste des agents (même si pas d'activité — ligne à 0)
    # ----------------------------------------------------------------
    res_agents = await db.execute(
        select(Agent, Departement)
        .outerjoin(Departement, Departement.id == Agent.departement_id)
        .where(Agent.tenant_id == superviseur.tenant_id)
        .order_by(Agent.nom, Agent.prenom)
    )
    lignes: list[StatistiquesActiviteAgent] = []
    for agent, dep in res_agents:
        c = compteurs.get(agent.id, {})
        a_traiter, en_retard = charge.get(agent.id, (0, 0))
        ligne = StatistiquesActiviteAgent(
            agent_id=agent.id,
            nom=agent.nom,
            prenom=agent.prenom,
            departement=dep.libelle if dep else None,
            fonction=agent.fonction,
            courriers_crees=c.get(ACTION_CREATION, 0),
            mises_en_copie=c.get(ACTION_COPIE, 0),
            imputations_emises=c.get(ACTION_IMPUTATION, 0),
            reponses_creees=c.get(ACTION_REPONSE, 0),
            courriers_envoyes=c.get(ACTION_ENVOI, 0),
            notes_ajoutees=c.get(ACTION_NOTE, 0),
            documents_ajoutes=c.get(ACTION_AJOUT_DOCUMENT, 0),
            validations_demandees=c.get(ACTION_DEMANDE_VALIDATION, 0),
            validations_accordees=c.get(ACTION_VALIDATION, 0),
            courriers_a_traiter=a_traiter,
            courriers_en_retard=en_retard,
        )
        lignes.append(ligne)

    return StatistiquesActiviteReponse(
        date_debut=date_debut,
        date_fin=date_fin,
        agents=lignes,
    )
