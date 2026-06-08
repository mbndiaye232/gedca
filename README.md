# Soft GEDCAP — Web

**Soft GEDCAP** — **G**estion **É**lectronique de **D**ocuments, **C**ourriers et **A**rchives **P**hysiques.

Conversion en stack web moderne de l'application desktop WinDev historique « SOFT GED-GEC-ARCHIVAGE » (2S Technology, Dakar).

## Statut

🚧 **Phase de cadrage** — pas encore de code. Les documents de référence sont :

- [`CLAUDE.md`](./CLAUDE.md) — instructions complètes pour Claude Code et l'équipe.
- [`docs/schema.md`](./docs/schema.md) — schéma PostgreSQL initial.
- [`docs/ecrans.md`](./docs/ecrans.md) — inventaire des écrans à reproduire, priorisés.
- [`docs/guidesoftgedca.pdf`](./docs/guidesoftgedca.pdf) — guide d'utilisation de l'app desktop d'origine.
- [`bdsoftged/`](./bdsoftged/) — tables HyperFile SQL de l'app desktop (référence sémantique, **données de test non migrées**).

## Stack cible

- **Backend** : Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic
- **Worker** : Celery + Redis
- **Base** : PostgreSQL 16 + pgvector + FTS française
- **Frontend** : React + Vite + TypeScript + Tailwind + shadcn/ui
- **Déploiement** : hybride — SaaS cloud multi-tenant + Docker Compose on-premise

## Modes de déploiement

| Mode | Cible | Multi-tenant | IA |
|---|---|---|---|
| SaaS cloud | Render (API + Worker + PostgreSQL + Redis) + Cloudflare Pages (frontend) | Oui, `tenant_id` sur toutes les tables | Anthropic API |
| On-premise | `docker-compose up` chez le client | Non, `tenant_id` fixe | Ollama + e5-large |

## Prochaines étapes

1. ⬜ Squelette monorepo (`backend/`, `frontend/`, `worker/`, `docker-compose.yml`).
2. ⬜ Migrations Alembic initiales (cf. `docs/schema.md`).
3. ⬜ Auth JWT + agents + départements + audit_log.
4. ⬜ Stockage chiffré AES-256-GCM + table `documents`.
5. ⬜ Worker OCR + embeddings.
6. ⬜ Modules GED, GEC, Archivage (cf. `docs/ecrans.md`).

## Licence

Propriétaire — 2S Technology / Mame Mbaye NDIAYE.
