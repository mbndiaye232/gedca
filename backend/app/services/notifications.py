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

Connectez-vous à GEDCA pour le traiter :
{{ url_gedca }}/courriers/{{ courrier_id }}

— Notification automatique GEDCA
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
