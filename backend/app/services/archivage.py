"""Service métier de l'archivage physique.

Concentre :
- L'auto-numérotation des `numero` au sein d'un parent (lock SQL).
- Le calcul du code complet `SS.LL.RR.BBB.DD.SD` via la vue `v_sous_dossiers_code`.
- La vérification « pas d'enfants » avant suppression.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


async def prochain_numero(
    db: AsyncSession,
    model: Any,
    *,
    parent_column: Any,
    parent_value: int,
    cap: int,
    type_emplacement: str,
) -> int:
    """Calcule le prochain `numero` libre pour un parent donné.

    Utilise un `SELECT ... FOR UPDATE` sur le verrou de l'ID parent pour
    éviter les courses concurrentes lors de la création quasi simultanée
    de deux enfants.

    Args:
        db : session SQLAlchemy.
        model : classe modèle de l'enfant (Site, LocalSalle, Rayon, …).
        parent_column : colonne FK vers le parent (ou `Site.tenant_id` pour les sites).
        parent_value : valeur de cette colonne.
        cap : valeur max autorisée (99 ou 999).
        type_emplacement : libellé du niveau pour les messages d'erreur.

    Lève HTTPException 409 si le cap est atteint.
    """
    # Verrouille les lignes existantes pour ce parent pendant la transaction.
    # Évite qu'une autre requête concurrente lise le même MAX et émette
    # le même numero — la contrainte UNIQUE attraperait sinon avec un 409
    # moins explicite.
    await db.execute(
        select(model)
        .where(parent_column == parent_value)
        .with_for_update()
    )

    courant = await db.scalar(
        select(func.coalesce(func.max(model.numero), 0)).where(parent_column == parent_value)
    )
    prochain = int(courant or 0) + 1
    if prochain > cap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Limite atteinte : {cap} {type_emplacement} max par parent",
        )
    return prochain


async def verifier_pas_d_enfants(
    db: AsyncSession,
    *,
    enfant_table: str,
    parent_column: str,
    parent_id: int,
    libelle_enfant: str,
) -> None:
    """Lève HTTP 409 si au moins un enfant existe pour ce parent.

    On utilise du SQL brut paramétré pour rester indépendant du modèle —
    le service appelant n'a pas besoin d'importer toute la chaîne d'enfants.
    """
    if not enfant_table.replace("_", "").isalpha():
        raise ValueError("enfant_table doit être un identifiant SQL simple")
    if not parent_column.replace("_", "").isalpha():
        raise ValueError("parent_column doit être un identifiant SQL simple")

    sql = text(
        f"SELECT COUNT(*) FROM {enfant_table} WHERE {parent_column} = :pid"
    )
    nb = await db.scalar(sql, {"pid": parent_id})
    if nb and int(nb) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Suppression impossible : {int(nb)} {libelle_enfant}(s) "
                "rattaché(s). Supprime-les d'abord."
            ),
        )


async def code_complet_sous_dossier(
    db: AsyncSession, sous_dossier_id: int, tenant_id: int
) -> dict[str, Any] | None:
    """Renvoie le code dotté + libellés et numéros des 6 niveaux pour un sous-dossier.

    Renvoie None si le sous-dossier n'existe pas ou appartient à un autre tenant.

    On fait un JOIN explicite plutôt que d'utiliser la vue `v_sous_dossiers_code` —
    cette dernière n'expose que les libellés. Le code complet est recalculé
    avec le même format SQL `'%02s.%02s.%02s.%03s.%02s.%02s'`.
    """
    sql = text(
        """
        SELECT
            sd.id AS sous_dossier_id,
            format('%02s.%02s.%02s.%03s.%02s.%02s',
                s.numero, l.numero, r.numero, b.numero, d.numero, sd.numero
            ) AS code_complet,
            s.numero AS site_numero, s.libelle AS site_libelle,
            l.numero AS local_numero, l.libelle AS local_libelle,
            r.numero AS rayon_numero, r.libelle AS rayon_libelle,
            b.numero AS boite_numero, b.libelle AS boite_libelle,
            d.numero AS dossier_numero, d.libelle AS dossier_libelle,
            sd.numero AS sous_dossier_numero, sd.libelle AS sous_dossier_libelle
        FROM sous_dossiers sd
        JOIN dossiers_classeurs d ON d.id = sd.dossier_id
        JOIN boites b              ON b.id = d.boite_id
        JOIN rayons r              ON r.id = b.rayon_id
        JOIN locaux_salles l       ON l.id = r.local_id
        JOIN sites s               ON s.id = l.site_id
        WHERE sd.id = :sd_id AND s.tenant_id = :t_id
        """
    )
    row = (await db.execute(sql, {"sd_id": sous_dossier_id, "t_id": tenant_id})).mappings().first()
    if row is None:
        return None
    return dict(row)
