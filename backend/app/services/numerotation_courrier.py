"""Numérotation automatique des courriers : YYYY-NNNNNN, reset annuel par tenant.

Concurrence : pour éviter que 2 créations simultanées ne produisent le même
numéro, on utilise un advisory lock PostgreSQL portant le couple
(tenant_id, année). Au pire, la 2e attendra que la 1re commit avant
de calculer son propre MAX(numero).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def prochain_numero_enregistrement(
    db: AsyncSession, tenant_id: int, annee: int | None = None
) -> str:
    """Retourne le prochain numéro disponible au format YYYY-NNNNNN.

    Args:
        db : session SQLAlchemy.
        tenant_id : tenant courant.
        annee : année cible. Si None, prend l'année courante côté serveur.

    Sécurité concurrence : `pg_advisory_xact_lock(key1, key2)` posé sur
    (tenant_id, année). Tenu jusqu'à la fin de la transaction courante
    (commit ou rollback). Évite la course classique
    « 2 sessions lisent MAX = N, écrivent N+1 ».
    """
    if annee is None:
        annee = datetime.now().year

    # Advisory lock par (tenant, année). Bloque les autres sessions au même
    # couple de clés jusqu'au commit/rollback.
    await db.execute(
        text("SELECT pg_advisory_xact_lock(:t, :a)"),
        {"t": tenant_id, "a": annee},
    )

    prefixe = f"{annee:04d}-"
    sql = text(
        """
        SELECT COALESCE(MAX(
            CAST(SUBSTRING(numero_enregistrement FROM 6) AS INTEGER)
        ), 0)
        FROM courriers
        WHERE tenant_id = :t
          AND numero_enregistrement LIKE :prefixe
        """
    )
    courant = await db.scalar(sql, {"t": tenant_id, "prefixe": f"{prefixe}%"})
    prochain = int(courant or 0) + 1
    return f"{prefixe}{prochain:06d}"
