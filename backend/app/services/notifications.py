"""Service d'envoi de notifications email (PRD-06A).

Stratégie d'implémentation 06A
- Asyncio.create_task → fire-and-forget. Non bloquant pour la requête HTTP.
- Si le tenant n'a pas de SMTP configuré : log silencieux dans audit_log
  (action `courrier.notification_skipped`), pas d'exception remontée.
- Si l'envoi échoue (timeout, refus serveur) : audit_log
  (action `courrier.notification_echouee`) avec la cause.

Migration future (PRD-03 ou PRD-06B)
- Remplacer `asyncio.create_task` par une tâche Celery réelle pour
  bénéficier des retries automatiques et du suivi de queue.
"""

from __future__ import annotations

import asyncio
import logging

import aiosmtplib
from email.message import EmailMessage
from jinja2 import Template
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import engine
from app.models import Agent, Courrier, Tenant
from app.services.audit import journaliser
from app.services.crypto import dechiffrer

logger = logging.getLogger("gedca.notifications")


# Templates Jinja2 minimaux — inline pour éviter une dépendance fichiers.
TEMPLATE_NOUVEAU_COURRIER = Template(
    """\
Bonjour {{ prenom }},

Un nouveau courrier vient d'être enregistré et vous est destiné.

Numéro : {{ numero }}
Sens : {{ sens }}
Objet : {{ objet }}
{% if date_limite %}Date limite de traitement : {{ date_limite }}{% endif %}

Connectez-vous à Soft GEDCAP pour le traiter :
{{ url_gedca }}/courriers/{{ courrier_id }}

— Notification automatique Soft GEDCAP
"""
)

# Mise en copie — envoyée à chaque agent nouvellement ajouté en copie
TEMPLATE_MISE_EN_COPIE = Template(
    """\
Bonjour {{ prenom }},

{{ ajouteur_prenom }} {{ ajouteur_nom }} vous a mis en copie d'un courrier.

Numéro : {{ numero }}
Sens : {{ sens }}
Objet : {{ objet }}
{% if date_limite %}Date limite de traitement : {{ date_limite }}{% endif %}

Vous pouvez le consulter depuis la corbeille « En copie » :
{{ url_gedca }}/courriers/{{ courrier_id }}

— Notification automatique Soft GEDCAP
"""
)

# Alerte de retard — envoyée à propriétaire + agents en copie
TEMPLATE_ALERTE_RETARD = Template(
    """\
Bonjour {{ prenom }},

{% if palier == 0 -%}
La date limite de traitement d'un courrier est atteinte AUJOURD'HUI.
{%- elif palier == 1 -%}
La date limite de traitement d'un courrier est DEMAIN.
{%- else -%}
La date limite de traitement d'un courrier est dans {{ palier }} jours.
{%- endif %}

Numéro : {{ numero }}
Objet : {{ objet }}
Date limite : {{ date_limite }}

Pour traiter ce courrier :
{{ url_gedca }}/courriers/{{ courrier_id }}

— Notification automatique Soft GEDCAP
"""
)

# PRD-06B — Demande de validation envoyée à l'agent valideur
TEMPLATE_DEMANDE_VALIDATION = Template(
    """\
Bonjour {{ prenom }},

{{ demandeur_prenom }} {{ demandeur_nom }} vous demande de valider un courrier.

Numéro : {{ numero }}
Objet : {{ objet }}
{% if instruction %}
Instruction du demandeur :
{{ instruction }}
{% endif %}
Connectez-vous à Soft GEDCAP, ouvrez la corbeille « À valider »,
puis cliquez sur « Valider » après vérification :
{{ url_gedca }}/courriers/{{ courrier_id }}

— Notification automatique Soft GEDCAP
"""
)

# PRD-06B — Confirmation de validation envoyée au demandeur initial
TEMPLATE_VALIDATION_ACCORDEE = Template(
    """\
Bonjour {{ prenom }},

{{ valideur_prenom }} {{ valideur_nom }} a validé votre courrier.

Numéro : {{ numero }}
Objet : {{ objet }}

Vous pouvez maintenant l'envoyer depuis votre corbeille « Validés » :
{{ url_gedca }}/courriers/{{ courrier_id }}

— Notification automatique Soft GEDCAP
"""
)


async def notifier_nouveau_courrier(
    courrier_id: int, agent_destinataire_id: int, tenant_id: int
) -> None:
    """Lance l'envoi d'une notification email en arrière-plan.

    Utilise une nouvelle session DB (la session de la requête HTTP est
    peut-être déjà fermée au moment de l'envoi).
    Toute exception est attrapée et loggée — l'appelant ne doit jamais voir
    d'erreur de notification.
    """

    async def _envoyer() -> None:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            try:
                # Charger tenant + destinataire + courrier
                tenant = await db.get(Tenant, tenant_id)
                agent = await db.get(Agent, agent_destinataire_id)
                courrier = await db.get(Courrier, courrier_id)
                if not tenant or not agent or not courrier:
                    logger.warning("Notification : entité manquante (skip)")
                    return

                # SMTP non configuré → audit log et stop
                if not tenant.smtp_host or not tenant.smtp_user:
                    await journaliser(
                        db,
                        tenant_id=tenant_id,
                        action="courrier.notification_skipped",
                        entite="courriers",
                        entite_id=courrier_id,
                        payload={
                            "raison": "smtp_non_configure",
                            "destinataire_id": agent_destinataire_id,
                        },
                    )
                    await db.commit()
                    return

                if not agent.email:
                    await journaliser(
                        db,
                        tenant_id=tenant_id,
                        action="courrier.notification_skipped",
                        entite="courriers",
                        entite_id=courrier_id,
                        payload={
                            "raison": "destinataire_sans_email",
                            "destinataire_id": agent_destinataire_id,
                        },
                    )
                    await db.commit()
                    return

                # Déchiffrer le mot de passe SMTP
                smtp_password = ""
                if tenant.smtp_password_enc:
                    try:
                        smtp_password = dechiffrer(
                            tenant.smtp_password_enc, tenant.id, usage="smtp"
                        ).decode("utf-8")
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Déchiffrement SMTP password échoué: %s", exc)
                        await journaliser(
                            db,
                            tenant_id=tenant_id,
                            action="courrier.notification_echouee",
                            entite="courriers",
                            entite_id=courrier_id,
                            payload={"raison": "smtp_password_invalide"},
                        )
                        await db.commit()
                        return

                # Construire le message
                corps = TEMPLATE_NOUVEAU_COURRIER.render(
                    prenom=agent.prenom,
                    numero=courrier.numero_enregistrement,
                    sens=courrier.sens,
                    objet=courrier.objet,
                    date_limite=courrier.date_limite,
                    courrier_id=courrier_id,
                    url_gedca=tenant.smtp_from or "http://localhost:5173",
                )
                msg = EmailMessage()
                msg["From"] = tenant.smtp_from or tenant.smtp_user
                msg["To"] = agent.email
                msg["Subject"] = (
                    f"[GEDCA] Nouveau courrier {courrier.numero_enregistrement} — "
                    f"{courrier.objet[:80]}"
                )
                msg.set_content(corps)

                # Envoyer via aiosmtplib
                await aiosmtplib.send(
                    msg,
                    hostname=tenant.smtp_host,
                    port=tenant.smtp_port or 587,
                    username=tenant.smtp_user,
                    password=smtp_password,
                    use_tls=False,
                    start_tls=bool(tenant.smtp_use_tls),
                    timeout=10,
                )

                await journaliser(
                    db,
                    tenant_id=tenant_id,
                    action="courrier.notification_envoyee",
                    entite="courriers",
                    entite_id=courrier_id,
                    payload={
                        "destinataire_id": agent_destinataire_id,
                        "destinataire_email": agent.email,
                    },
                )
                await db.commit()
                logger.info(
                    "Notification courrier %s envoyée à %s",
                    courrier.numero_enregistrement,
                    agent.email,
                )

            except Exception as exc:  # noqa: BLE001
                logger.exception("Notification email échouée: %s", exc)
                try:
                    await journaliser(
                        db,
                        tenant_id=tenant_id,
                        action="courrier.notification_echouee",
                        entite="courriers",
                        entite_id=courrier_id,
                        payload={
                            "destinataire_id": agent_destinataire_id,
                            "erreur": str(exc)[:500],
                        },
                    )
                    await db.commit()
                except Exception:  # noqa: BLE001, S110
                    pass

    # Fire-and-forget : on schedule l'envoi sans attendre
    asyncio.create_task(_envoyer())


# ---------------------------------------------------------------------------
# Helper interne pour les notifications PRD-06B (workflow validation)
# ---------------------------------------------------------------------------


async def _envoyer_email_simple(
    *,
    tenant_id: int,
    destinataire_agent_id: int,
    sujet: str,
    corps: str,
    courrier_id: int,
    action_audit: str,
) -> None:
    """Envoie un email simple à un agent du tenant.

    Charge tenant + agent, vérifie SMTP, envoie via aiosmtplib, journalise.
    Toute exception est attrapée et loggée.
    """
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        try:
            tenant = await db.get(Tenant, tenant_id)
            agent = await db.get(Agent, destinataire_agent_id)
            if not tenant or not agent:
                logger.warning(
                    "Notification %s : entité manquante (tenant=%s, agent=%s)",
                    action_audit,
                    tenant_id,
                    destinataire_agent_id,
                )
                return

            if not tenant.smtp_host or not tenant.smtp_user or not agent.email:
                await journaliser(
                    db,
                    tenant_id=tenant_id,
                    action=f"{action_audit}_skipped",
                    entite="courriers",
                    entite_id=courrier_id,
                    payload={
                        "raison": (
                            "smtp_non_configure"
                            if not tenant.smtp_host
                            else "destinataire_sans_email"
                        ),
                        "destinataire_id": destinataire_agent_id,
                    },
                )
                await db.commit()
                return

            smtp_password = ""
            if tenant.smtp_password_enc:
                try:
                    smtp_password = dechiffrer(
                        tenant.smtp_password_enc, tenant.id, usage="smtp"
                    ).decode("utf-8")
                except Exception as exc:  # noqa: BLE001
                    logger.error("Déchiffrement SMTP password échoué: %s", exc)
                    return

            msg = EmailMessage()
            msg["From"] = tenant.smtp_from or tenant.smtp_user
            msg["To"] = agent.email
            msg["Subject"] = sujet
            msg.set_content(corps)

            await aiosmtplib.send(
                msg,
                hostname=tenant.smtp_host,
                port=tenant.smtp_port or 587,
                username=tenant.smtp_user,
                password=smtp_password,
                use_tls=False,
                start_tls=bool(tenant.smtp_use_tls),
                timeout=10,
            )

            await journaliser(
                db,
                tenant_id=tenant_id,
                action=action_audit,
                entite="courriers",
                entite_id=courrier_id,
                payload={"destinataire_id": destinataire_agent_id},
            )
            await db.commit()

        except Exception as exc:  # noqa: BLE001
            logger.exception("Notification %s échouée: %s", action_audit, exc)


async def notifier_demande_validation(
    courrier_id: int,
    agent_valideur_id: int,
    agent_demandeur_id: int,
    tenant_id: int,
    instruction: str | None = None,
) -> None:
    """Notifie l'agent valideur qu'un courrier attend sa validation.

    Fire-and-forget. PRD-06B.
    """

    async def _envoyer() -> None:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            try:
                valideur = await db.get(Agent, agent_valideur_id)
                demandeur = await db.get(Agent, agent_demandeur_id)
                courrier = await db.get(Courrier, courrier_id)
                tenant = await db.get(Tenant, tenant_id)
                if not (valideur and demandeur and courrier and tenant):
                    return

                corps = TEMPLATE_DEMANDE_VALIDATION.render(
                    prenom=valideur.prenom,
                    demandeur_prenom=demandeur.prenom,
                    demandeur_nom=demandeur.nom,
                    numero=courrier.numero_enregistrement,
                    objet=courrier.objet,
                    instruction=instruction,
                    courrier_id=courrier_id,
                    url_gedca=tenant.smtp_from or "http://localhost:5173",
                )
                sujet = (
                    f"[Soft GEDCAP] Demande de validation — "
                    f"{courrier.numero_enregistrement}"
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Préparation notification validation: %s", exc)
                return

        # L'envoi proprement dit (rouvre sa propre session)
        await _envoyer_email_simple(
            tenant_id=tenant_id,
            destinataire_agent_id=agent_valideur_id,
            sujet=sujet,
            corps=corps,
            courrier_id=courrier_id,
            action_audit="courrier.notif_demande_validation",
        )

    asyncio.create_task(_envoyer())


async def notifier_courrier_valide(
    courrier_id: int,
    agent_demandeur_id: int,
    agent_valideur_id: int,
    tenant_id: int,
) -> None:
    """Notifie le demandeur initial que son courrier vient d'être validé.

    Fire-and-forget. PRD-06B.
    """

    async def _envoyer() -> None:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            try:
                demandeur = await db.get(Agent, agent_demandeur_id)
                valideur = await db.get(Agent, agent_valideur_id)
                courrier = await db.get(Courrier, courrier_id)
                tenant = await db.get(Tenant, tenant_id)
                if not (demandeur and valideur and courrier and tenant):
                    return

                corps = TEMPLATE_VALIDATION_ACCORDEE.render(
                    prenom=demandeur.prenom,
                    valideur_prenom=valideur.prenom,
                    valideur_nom=valideur.nom,
                    numero=courrier.numero_enregistrement,
                    objet=courrier.objet,
                    courrier_id=courrier_id,
                    url_gedca=tenant.smtp_from or "http://localhost:5173",
                )
                sujet = (
                    f"[Soft GEDCAP] Courrier validé — "
                    f"{courrier.numero_enregistrement}"
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Préparation notification valide: %s", exc)
                return

        await _envoyer_email_simple(
            tenant_id=tenant_id,
            destinataire_agent_id=agent_demandeur_id,
            sujet=sujet,
            corps=corps,
            courrier_id=courrier_id,
            action_audit="courrier.notif_validation",
        )

    asyncio.create_task(_envoyer())


# ---------------------------------------------------------------------------
# Mise en copie
# ---------------------------------------------------------------------------


async def notifier_mise_en_copie(
    courrier_id: int,
    agent_en_copie_id: int,
    agent_ajouteur_id: int,
    tenant_id: int,
) -> None:
    """Notifie un agent qu'il vient d'être mis en copie d'un courrier.

    Fire-and-forget. Appelé par POST /courriers/{id}/copies une fois par
    agent nouvellement ajouté.
    """

    async def _envoyer() -> None:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            try:
                en_copie = await db.get(Agent, agent_en_copie_id)
                ajouteur = await db.get(Agent, agent_ajouteur_id)
                courrier = await db.get(Courrier, courrier_id)
                tenant = await db.get(Tenant, tenant_id)
                if not (en_copie and ajouteur and courrier and tenant):
                    return

                corps = TEMPLATE_MISE_EN_COPIE.render(
                    prenom=en_copie.prenom,
                    ajouteur_prenom=ajouteur.prenom,
                    ajouteur_nom=ajouteur.nom,
                    numero=courrier.numero_enregistrement,
                    sens=courrier.sens,
                    objet=courrier.objet,
                    date_limite=courrier.date_limite,
                    courrier_id=courrier_id,
                    url_gedca=tenant.smtp_from or "http://localhost:5173",
                )
                sujet = (
                    f"[Soft GEDCAP] Mis en copie — "
                    f"{courrier.numero_enregistrement}"
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Préparation notification copie: %s", exc)
                return

        await _envoyer_email_simple(
            tenant_id=tenant_id,
            destinataire_agent_id=agent_en_copie_id,
            sujet=sujet,
            corps=corps,
            courrier_id=courrier_id,
            action_audit="courrier.notif_copie",
        )

    asyncio.create_task(_envoyer())


# ---------------------------------------------------------------------------
# Alerte de retard
# ---------------------------------------------------------------------------


async def notifier_alerte_retard(
    courrier_id: int,
    agent_id: int,
    palier: int,
    tenant_id: int,
) -> None:
    """Notifie un agent qu'un de ses courriers approche de la date limite.

    `palier` ∈ {5, 3, 2, 1, 0} — jours restants. Fire-and-forget.
    L'anti-doublon est géré par le caller (table `alertes_retard_envoyees`).
    """

    async def _envoyer() -> None:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            try:
                cible = await db.get(Agent, agent_id)
                courrier = await db.get(Courrier, courrier_id)
                tenant = await db.get(Tenant, tenant_id)
                if not (cible and courrier and tenant):
                    return

                corps = TEMPLATE_ALERTE_RETARD.render(
                    prenom=cible.prenom,
                    palier=palier,
                    numero=courrier.numero_enregistrement,
                    objet=courrier.objet,
                    date_limite=courrier.date_limite,
                    courrier_id=courrier_id,
                    url_gedca=tenant.smtp_from or "http://localhost:5173",
                )
                sujet_label = (
                    "AUJOURD'HUI"
                    if palier == 0
                    else f"J-{palier}"
                )
                sujet = (
                    f"[Soft GEDCAP] Alerte échéance ({sujet_label}) — "
                    f"{courrier.numero_enregistrement}"
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Préparation alerte retard: %s", exc)
                return

        await _envoyer_email_simple(
            tenant_id=tenant_id,
            destinataire_agent_id=agent_id,
            sujet=sujet,
            corps=corps,
            courrier_id=courrier_id,
            action_audit=f"courrier.alerte_retard_j{palier}",
        )

    asyncio.create_task(_envoyer())
