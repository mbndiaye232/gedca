"""Tâches d'extraction de texte des documents.

Conçues pour être lancées en arrière-plan via FastAPI `BackgroundTasks`
(même process, après l'envoi de la réponse HTTP). Aucune dépendance Celery
nécessaire en Phase 1 — on migrera vers Celery quand le volume le justifiera
(>100 docs/min ou besoin de retry sophistiqué).

Idempotent : rejouer la tâche sur un document déjà extrait écrase simplement
le `texte_ocr` et le `statut`.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.db import async_session_factory
from app.models import Document
from app.services.extraction import ExtractionError, extraire_texte
from app.services.storage import StorageError, lire_dechiffre

logger = logging.getLogger(__name__)

# Statuts conventionnés (chaînes simples — pas d'enum dédiée)
STATUT_PRET = "pret"
STATUT_OCR_EN_ATTENTE = "ocr_en_attente"
STATUT_OCR_ECHOUE = "ocr_echoue"


async def extraire_et_indexer(document_id: int, tenant_id: int) -> None:
    """Charge, déchiffre, extrait le texte, met à jour le document.

    Args:
        document_id: id du document à traiter.
        tenant_id: garde-fou multi-tenant — le doc doit appartenir à ce tenant.

    Le statut final du document devient :
    - `pret` : extraction réussie (le trigger Postgres met à jour `recherche_fts`
      automatiquement quand `texte_ocr` change)
    - `ocr_echoue` : Tesseract absent, fichier corrompu, format non supporté
      non fatal → le doc reste utilisable, juste non indexé
    """
    async with async_session_factory() as session:
        try:
            doc = await session.scalar(
                select(Document).where(
                    Document.id == document_id,
                    Document.tenant_id == tenant_id,
                    Document.supprime.is_(False),
                )
            )
            if doc is None:
                logger.warning(
                    "Extraction : document %s introuvable ou supprimé "
                    "(tenant=%s)",
                    document_id,
                    tenant_id,
                )
                return

            try:
                contenu = await lire_dechiffre(doc.chemin_stockage, tenant_id)
            except StorageError as exc:
                logger.error(
                    "Extraction doc %s : fichier introuvable sur disque : %s",
                    document_id,
                    exc,
                )
                doc.texte_ocr = None
                doc.statut = STATUT_OCR_ECHOUE
                await session.commit()
                return

            try:
                resultat = extraire_texte(contenu, doc.mime)
            except ExtractionError as exc:
                logger.warning(
                    "Extraction doc %s (%s) : %s",
                    document_id,
                    doc.mime,
                    exc,
                )
                doc.statut = STATUT_OCR_ECHOUE
                await session.commit()
                return

            # Le trigger PG met à jour recherche_fts dès qu'on touche texte_ocr
            doc.texte_ocr = resultat.texte or None
            doc.statut = STATUT_PRET
            await session.commit()

            logger.info(
                "Extraction doc %s OK : méthode=%s, pages_ocr=%s, "
                "texte=%s chars",
                document_id,
                resultat.methode,
                resultat.pages_traitees,
                len(resultat.texte),
            )

        except Exception:
            # Filet de sécurité — on ne veut pas qu'une exception non
            # gérée tue le worker. On log et on tente de marquer le doc.
            logger.exception(
                "Extraction doc %s : exception inattendue", document_id
            )
            try:
                await session.rollback()
                doc2 = await session.get(Document, document_id)
                if doc2 is not None and doc2.tenant_id == tenant_id:
                    doc2.statut = STATUT_OCR_ECHOUE
                    await session.commit()
            except Exception:
                logger.exception(
                    "Extraction doc %s : impossible de marquer ocr_echoue",
                    document_id,
                )
