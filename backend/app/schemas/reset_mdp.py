"""Schémas Pydantic pour la réinitialisation de mot de passe."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TokenValideReponse(BaseModel):
    """Réponse de POST /auth/reset-mdp/verifier — confirmation que le
    token est valide, sans exposer d'info sensible.

    On renvoie juste le prénom pour personnaliser l'écran ("Bonjour
    Mame, choisis ton nouveau mot de passe").
    """

    valide: bool
    prenom: str | None = None


class ChangerMdpAvecTokenBody(BaseModel):
    """Body de POST /auth/reset-mdp/changer."""

    token: str = Field(..., min_length=10, max_length=128)
    nouveau_mot_de_passe: str = Field(..., min_length=8, max_length=255)


class ResetMdpInitieReponse(BaseModel):
    """Réponse de POST /agents/{id}/reset-mdp/initier (superviseur).

    On indique simplement que le mail a été envoyé (ou skippé si SMTP
    non configuré). Le token n'est jamais exposé dans la réponse HTTP.
    """

    email_envoye: bool
    destinataire_email: str | None
    duree_validite_heures: int = 24
