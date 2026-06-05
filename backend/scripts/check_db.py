"""Diagnostic rapide de l'etat de la base gedca."""

from __future__ import annotations

import asyncio
import os
import sys

import asyncpg


async def main() -> None:
    # Force UTF-8 stdout pour eviter UnicodeEncodeError sur Windows cp1252
    sys.stdout.reconfigure(encoding="utf-8")

    url = os.environ.get("DATABASE_URL", "")
    print(f"DATABASE_URL = {url}\n")

    c = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="gedca",
        password="gedca_dev_password",
        database="gedca",
    )

    print("a) Tables dans la base 'gedca':")
    rows = await c.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
    )
    if not rows:
        print("   (aucune table)")
    else:
        for r in rows:
            print(f"   - {r['tablename']}")
    print()

    if any(r["tablename"] == "alembic_version" for r in rows):
        v = await c.fetchval("SELECT version_num FROM alembic_version")
        print(f"b) Version Alembic appliquee: {v!r}")
        print()

    if any(r["tablename"] == "agents" for r in rows):
        print("c) Agents:")
        agents = await c.fetch(
            "SELECT id, tenant_id, login, actif, role_id FROM agents"
        )
        if not agents:
            print("   (aucun)")
        else:
            for a in agents:
                print(f"   - {dict(a)}")
    else:
        print("c) Pas de table agents")

    if any(r["tablename"] == "tenants" for r in rows):
        print()
        print("d) Tenants:")
        tenants = await c.fetch("SELECT id, code, raison_sociale FROM tenants")
        for t in tenants:
            print(f"   - {dict(t)}")

    await c.close()


if __name__ == "__main__":
    asyncio.run(main())
