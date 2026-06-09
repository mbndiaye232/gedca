"""Routes de configuration SMTP du tenant (superviseur).

- GET  /api/parametres-smtp/me        : lit la config (sans le mdp)
- PUT  /api/parametres-smtp/me        : modifie la config
- POST /api/parametres-smtp/me/tester : envoie un email test pour valider
"""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib
from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import AgentSuperviseur, IpClient, SessionDB
from app.models import Tenant
from app.schemas.parametres_smtp import (
    ParametresSmtpLecture,
    ParametresSmtpMiseAJour,
    ParametresSmtpTestBody,
    ParametresSmtpTestReponse,
)
from app.services.audit import journaliser
from app.services.crypto import chiffrer, dechiffrer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parametres-smtp", tags=["parametres-smtp"])


async def _charger_tenant(db: SessionDB, tenant_id: int) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant introuvable"
        )
    return tenant


def _to_lecture(tenant: Tenant) -> ParametresSmtpLecture:
    return ParametresSmtpLecture(
        smtp_host=tenant.smtp_host,
        smtp_port=tenant.smtp_port,
        smtp_user=tenant.smtp_user,
        smtp_from=tenant.smtp_from,
        smtp_use_tls=tenant.smtp_use_tls,
        password_defini=tenant.smtp_password_enc is not None,
    )


@router.get(
    "/me",
    response_model=ParametresSmtpLecture,
    summary="Lire la configuration SMTP de mon tenant (superviseur)",
)
async def lire(
    superviseur: AgentSuperviseur, db: SessionDB
) -> ParametresSmtpLecture:
    """Retourne la config SMTP sans le mot de passe.

    Le booléen `password_defini` permet à l'UI de proposer l'option
    « Conserver le mot de passe actuel » sans révéler le secret.
    """
    tenant = await _charger_tenant(db, superviseur.tenant_id)
    return _to_lecture(tenant)


@router.put(
    "/me",
    response_model=ParametresSmtpLecture,
    summary="Modifier la configuration SMTP de mon tenant (superviseur)",
)
async def mettre_a_jour(
    body: ParametresSmtpMiseAJour,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> ParametresSmtpLecture:
    """Met à jour les champs SMTP.

    Sémantique du `smtp_password` :
    - `None` (omis) → le mot de passe existant est conservé intact
    - `""` (chaîne vide) → le mot de passe est effacé
    - tout autre → chiffrement AES-256-GCM puis stockage en BYTEA
    """
    tenant = await _charger_tenant(db, superviseur.tenant_id)

    if body.smtp_host is not None:
        tenant.smtp_host = body.smtp_host or None
    if body.smtp_port is not None:
        tenant.smtp_port = body.smtp_port
    if body.smtp_user is not None:
        tenant.smtp_user = body.smtp_user or None
    if body.smtp_from is not None:
        tenant.smtp_from = body.smtp_from or None
    if body.smtp_use_tls is not None:
        tenant.smtp_use_tls = body.smtp_use_tls

    if body.smtp_password is not None:
        if body.smtp_password == "":
            tenant.smtp_password_enc = None
        else:
            tenant.smtp_password_enc = chiffrer(
                body.smtp_password.encode("utf-8"),
                tenant.id,
                usage="smtp",
            )

    await journaliser(
        db,
        tenant_id=tenant.id,
        agent_id=superviseur.id,
        action="parametres_smtp.maj",
        entite="tenants",
        entite_id=tenant.id,
        # On ne logue PAS la valeur du mdp (même chiffré) — juste l'info
        # binaire qu'il a été modifié
        payload={
            "host_modifie": body.smtp_host is not None,
            "password_modifie": body.smtp_password is not None,
        },
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    await db.refresh(tenant)
    return _to_lecture(tenant)


@router.post(
    "/me/tester",
    response_model=ParametresSmtpTestReponse,
    summary="Envoyer un email de test pour valider la config (superviseur)",
)
async def tester(
    body: ParametresSmtpTestBody,
    superviseur: AgentSuperviseur,
    db: SessionDB,
    request: Request,
    ip: IpClient,
) -> ParametresSmtpTestReponse:
    """Tente l'envoi d'un email de validation.

    Cible par défaut : email du superviseur. Permet de tester
    immédiatement après une modification sans devoir attendre un
    événement métier.
    """
    tenant = await _charger_tenant(db, superviseur.tenant_id)

    destinataire = body.destinataire or superviseur.email
    if not destinataire:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Aucun email destinataire — renseigne ton email dans ton "
                "profil ou fournis-en un dans le body."
            ),
        )

    if not tenant.smtp_host or not tenant.smtp_user or not tenant.smtp_password_enc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Configuration SMTP incomplète. Renseigne au minimum "
                "host, user et password."
            ),
        )

    # Déchiffrer le mdp en mémoire (sans le logger)
    try:
        smtp_password = dechiffrer(
            tenant.smtp_password_enc, tenant.id, usage="smtp"
        ).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.error("Déchiffrement SMTP password échoué : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mot de passe SMTP corrompu en base. Re-saisis-le.",
        ) from exc

    msg = EmailMessage()
    msg["From"] = tenant.smtp_from or tenant.smtp_user
    msg["To"] = destinataire
    msg["Subject"] = "[Soft GEDCAP] Test de configuration SMTP"
    msg.set_content(
        f"Bonjour {superviseur.prenom},\n\n"
        "Cet email confirme que votre configuration SMTP fonctionne.\n\n"
        f"Serveur : {tenant.smtp_host}:{tenant.smtp_port or 587}\n"
        f"Utilisateur : {tenant.smtp_user}\n"
        f"From : {tenant.smtp_from or tenant.smtp_user}\n"
        f"TLS : {'oui' if tenant.smtp_use_tls else 'non'}\n\n"
        "— Soft GEDCAP"
    )

    try:
        await aiosmtplib.send(
            msg,
            hostname=tenant.smtp_host,
            port=tenant.smtp_port or 587,
            username=tenant.smtp_user,
            password=smtp_password,
            use_tls=False,
            start_tls=bool(tenant.smtp_use_tls),
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        # On NE leak PAS le smtp_password dans le message, même en cas
        # d'erreur d'authentification verbeux côté serveur.
        message = str(exc)[:500]
        await journaliser(
            db,
            tenant_id=tenant.id,
            agent_id=superviseur.id,
            action="parametres_smtp.test_echec",
            entite="tenants",
            entite_id=tenant.id,
            payload={"erreur": message},
            ip=ip,
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()
        return ParametresSmtpTestReponse(
            envoye=False, destinataire=destinataire, erreur=message
        )

    await journaliser(
        db,
        tenant_id=tenant.id,
        agent_id=superviseur.id,
        action="parametres_smtp.test_ok",
        entite="tenants",
        entite_id=tenant.id,
        payload={"destinataire": destinataire},
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return ParametresSmtpTestReponse(envoye=True, destinataire=destinataire)
