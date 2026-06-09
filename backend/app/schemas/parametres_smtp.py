"""Schémas Pydantic pour la configuration SMTP du tenant."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class ParametresSmtpLecture(BaseModel):
    """Lecture de la config SMTP — le mot de passe n'est JAMAIS renvoyé.

    On expose juste un booléen `password_defini` qui permet à l'UI de
    distinguer « pas configuré » de « déjà configuré, à conserver » sans
    révéler le secret.
    """

    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_user: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True
    password_defini: bool = False


class ParametresSmtpMiseAJour(BaseModel):
    """Body de PUT /api/parametres-smtp/me.

    Si `smtp_password` est `None`, le mot de passe existant est conservé
    intact. Pour l'effacer, envoyer une chaîne vide.
    """

    smtp_host: str | None = Field(None, max_length=255)
    smtp_port: int | None = Field(None, ge=1, le=65535)
    smtp_user: str | None = Field(None, max_length=255)
    smtp_password: str | None = Field(None, max_length=255)
    smtp_from: str | None = Field(None, max_length=255)
    smtp_use_tls: bool | None = None


class ParametresSmtpTestBody(BaseModel):
    """Body de POST /api/parametres-smtp/me/tester.

    Si `destinataire` est omis, on envoie au superviseur qui déclenche
    le test (cas standard : il vérifie sa propre boîte).
    """

    destinataire: EmailStr | None = None


class ParametresSmtpTestReponse(BaseModel):
    """Réponse du test d'envoi."""

    envoye: bool
    destinataire: str
    erreur: str | None = None
