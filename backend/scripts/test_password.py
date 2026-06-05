"""Verifie que le mot de passe de l'admin matche bien en base."""

from __future__ import annotations

import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from app.db import async_session_factory
from app.models import Agent
from app.services.password import verifier_mot_de_passe


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(Agent).where(Agent.login == "admin"))
        agent = result.scalar_one_or_none()
        if agent is None:
            print("Aucun agent 'admin' en base")
            return

        print(f"Agent trouve : id={agent.id}, tenant_id={agent.tenant_id}, actif={agent.actif}")
        print(f"Hash bcrypt stocke : {agent.password_hash[:40]}...")
        print(f"Longueur hash : {len(agent.password_hash) if agent.password_hash else 0}")
        print()

        for mdp in ["changeme123", "Changeme123", "CHANGEME123", "admin", "password"]:
            ok = verifier_mot_de_passe(mdp, agent.password_hash)
            print(f"  {mdp!r:20s} -> {'OK' if ok else 'KO'}")


if __name__ == "__main__":
    asyncio.run(main())
