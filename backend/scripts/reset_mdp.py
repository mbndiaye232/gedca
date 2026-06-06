"""Réinitialise le mot de passe d'un agent.

Usage :
    python -m scripts.reset_mdp <login> <nouveau_mdp>
    python -m scripts.reset_mdp mbndiaye Password123!
"""

from __future__ import annotations

import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from app.db import async_session_factory
from app.models import Agent
from app.services.password import hacher_mot_de_passe


async def main() -> int:
    if len(sys.argv) != 3:
        print("Usage : python -m scripts.reset_mdp <login> <nouveau_mdp>")
        return 1
    login_cible, nouveau_mdp = sys.argv[1], sys.argv[2]

    async with async_session_factory() as session:
        result = await session.execute(select(Agent).where(Agent.login == login_cible))
        agent = result.scalar_one_or_none()
        if agent is None:
            print(f"Aucun agent avec le login '{login_cible}'")
            return 1
        agent.password_hash = hacher_mot_de_passe(nouveau_mdp)
        await session.commit()
        print(
            f"OK : mot de passe de {agent.prenom} {agent.nom} (login={login_cible}) "
            f"réinitialisé à : {nouveau_mdp}"
        )
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
