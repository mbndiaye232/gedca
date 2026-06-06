"""Diagnostic des courriers en base."""

from __future__ import annotations

import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import asyncpg


async def main() -> None:
    c = await asyncpg.connect(
        host="localhost",
        port=5434,
        user="gedca",
        password="gedca_dev_password",
        database="gedca",
    )

    print("--- Agents ---")
    rows = await c.fetch(
        "SELECT id, login, prenom, nom FROM agents ORDER BY id"
    )
    for r in rows:
        print(f"  #{r['id']} login={r['login']} {r['prenom']} {r['nom']}")
    print()

    print("--- Courriers ---")
    rows = await c.fetch(
        """
        SELECT
            c.id, c.numero_enregistrement, c.sens, c.objet,
            c.statut_id, c.agent_destinataire_id, c.agent_proprietaire_id, c.created_by
        FROM courriers c
        ORDER BY c.id
        """
    )
    if not rows:
        print("  (aucun courrier en base)")
    for r in rows:
        print(
            f"  #{r['id']} {r['numero_enregistrement']} sens={r['sens']} "
            f"statut={r['statut_id']} dest={r['agent_destinataire_id']} "
            f"proprio={r['agent_proprietaire_id']} createur={r['created_by']}"
        )
        print(f"      objet: {r['objet']}")

    await c.close()


if __name__ == "__main__":
    asyncio.run(main())
