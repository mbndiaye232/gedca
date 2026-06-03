# GEDCA — backend

API FastAPI + worker Celery. Voir `../CLAUDE.md` pour l'architecture globale.

## Lancer en local (sans Docker)

Pré-requis : Python 3.12, PostgreSQL 16 avec pgvector + pg_trgm + unaccent, Redis 7+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # ou .venv\Scripts\Activate.ps1 sous Windows
pip install -e ".[dev]"
cp ../.env.example ../.env         # adapter, notamment DATABASE_URL et MASTER_KEY
export $(grep -v '^#' ../.env | xargs)

# Appliquer la migration
alembic upgrade head

# Seed dev (tenant 'demo' + superviseur admin/changeme123)
python -m scripts.seed_dev

# Démarrer l'API
uvicorn app.main:app --reload
```

API disponible sur http://localhost:8000, docs interactives sur /docs.

## Lancer en local (avec Docker)

```bash
# Depuis la racine du repo
cp .env.example .env
docker compose up --build
```

Une fois les conteneurs prêts, exécuter une fois :

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed_dev
```

## Tests

```bash
# Base de test dédiée (à créer une fois)
createdb gedca_test
export DATABASE_URL="postgresql+asyncpg://gedca:gedca@localhost:5432/gedca_test"
alembic upgrade head

# Lancer les tests
pytest -q

# Avec couverture
pytest --cov=app --cov-report=term-missing
```

Les tests utilisent une stratégie de **rollback par test** : chaque test ouvre
une transaction et la roll-back à la fin, garantissant l'isolation totale
sans avoir à recréer le schéma entre chaque test.

## Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py            # dépendances FastAPI (agent_courant, RBAC, IP)
│   │   └── v1/                # routes versionnées
│   │       ├── auth.py
│   │       ├── agents.py
│   │       ├── departements.py
│   │       ├── structure.py
│   │       └── audit_log.py
│   ├── models/                # modèles SQLAlchemy
│   ├── schemas/               # schémas Pydantic
│   ├── services/              # logique métier sans dépendance FastAPI
│   │   ├── password.py        # bcrypt
│   │   ├── jwt.py             # signature/décodage JWT
│   │   ├── crypto.py          # AES-256-GCM, clé maître + HKDF par tenant
│   │   ├── audit.py           # helper journaliser()
│   │   └── echeances.py       # calcul de coloration des dates limites
│   ├── tasks/                 # tâches Celery (à venir, PRD-03)
│   ├── config.py              # Pydantic Settings
│   ├── db.py                  # engine async + session factory + get_db
│   ├── main.py                # app FastAPI
│   └── worker.py              # app Celery
├── alembic/                   # migrations
├── scripts/
│   └── seed_dev.py            # seed initial dev (tenant + admin)
└── tests/
```
