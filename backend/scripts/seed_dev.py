"""Seed de développement — crée un tenant de test + un superviseur initial.

À exécuter une seule fois après `alembic upgrade head`, idempotent (skip
si le tenant existe déjà).

Usage :
    python -m scripts.seed_dev

Configurable via variables d'env :
    SEED_TENANT_CODE   (défaut : 'demo')
    SEED_ADMIN_LOGIN   (défaut : 'admin')
    SEED_ADMIN_PASSWORD (défaut : 'changeme123')
"""

from __future__ import annotations

import asyncio
import os
import sys

# Force UTF-8 sur stdout pour éviter UnicodeEncodeError sur la console Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select

from app.db import async_session_factory
from app.models import Agent, Departement, Role, Tenant
from app.services.password import hacher_mot_de_passe


async def main() -> int:
    code_tenant = os.environ.get("SEED_TENANT_CODE", "demo")
    login_admin = os.environ.get("SEED_ADMIN_LOGIN", "admin")
    mdp_admin = os.environ.get("SEED_ADMIN_PASSWORD", "changeme123")

    async with async_session_factory() as session:
        # Tenant déjà présent ?
        result = await session.execute(select(Tenant).where(Tenant.code == code_tenant))
        existing_tenant = result.scalar_one_or_none()
        if existing_tenant is not None:
            print(f"Tenant '{code_tenant}' déjà présent (id={existing_tenant.id}). Skip.")
            return 0

        # Charger le rôle superviseur
        result = await session.execute(select(Role).where(Role.code == "superviseur"))
        role_sup = result.scalar_one()

        # Créer le tenant
        tenant = Tenant(
            code=code_tenant,
            raison_sociale="Organisation de démonstration",
            email="contact@demo.local",
            ai_provider="ollama",
        )
        session.add(tenant)
        await session.flush()

        # Département par défaut
        dep = Departement(tenant_id=tenant.id, libelle="Direction générale")
        session.add(dep)
        await session.flush()

        # Agent superviseur
        admin = Agent(
            tenant_id=tenant.id,
            login=login_admin,
            password_hash=hacher_mot_de_passe(mdp_admin),
            auth_provider="local",
            nom="Administrateur",
            prenom="Super",
            email="admin@demo.local",
            fonction="Superviseur",
            departement_id=dep.id,
            role_id=role_sup.id,
            actif=True,
        )
        session.add(admin)
        await session.commit()

        print("✔ Seed terminé :")
        print(f"  Tenant : {tenant.code} (id={tenant.id})")
        print(f"  Département : {dep.libelle} (id={dep.id})")
        print(f"  Superviseur : {admin.login} / {mdp_admin} (id={admin.id})")
        print()
        print("⚠ Change le mot de passe immédiatement en production.")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
