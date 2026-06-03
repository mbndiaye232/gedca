# PRD-00 — Vision & Architecture GEDCA

| Champ        | Valeur                                                          |
|--------------|-----------------------------------------------------------------|
| **ID**       | PRD-00                                                          |
| **Module**   | Transverse                                                      |
| **Statut**   | Approuvé                                                        |
| **Auteur**   | mbndiaye232                                                     |
| **Date**     | 2026-05-31                                                      |
| **Dépend de**| —                                                               |

---

## 1. Contexte & problème

**SOFT GED-GEC-ARCHIVAGE** est une application desktop WinDev développée par 2S Technology, actuellement déployée chez plusieurs clients. Elle couvre trois fonctions métier interdépendantes : la gestion électronique de documents (GED), la gestion électronique de courriers (GEC) et l'archivage physique à 6 niveaux hiérarchiques.

Les contraintes de l'app desktop (mono-poste, base HyperFile SQL non exposable en réseau étendu, absence d'accès mobile, impossibilité de déploiement SaaS) limitent l'adoption et la valeur commerciale du produit.

**GEDCA** est la conversion de cette application vers une stack web moderne, conservant 100 % de la logique métier existante tout en ajoutant la recherche sémantique, l'ingestion automatique et un mode SaaS multi-tenant. La référence métier prioritaire reste le guide d'utilisation `docs/guidesoftgedca.pdf` ; chaque décision fonctionnelle qui s'en écarte doit être documentée.

## 2. Objectifs

- OBJ-1 : Reproduire fidèlement les trois modules métier de l'app desktop (GED, GEC, Archivage) avec leur vocabulaire et leurs règles métier.
- OBJ-2 : Offrir un déploiement **on-premise** (`docker-compose up`) fonctionnellement identique au déploiement **SaaS multi-tenant**.
- OBJ-3 : Apporter une valeur ajoutée mesurable par rapport au desktop : OCR automatique, recherche plein texte + sémantique, ingestion multi-sources (upload, dossier surveillé, IMAP).
- OBJ-4 : Garantir l'isolement des données entre tenants — aucune fuite entre organisations clientes.
- OBJ-5 : Permettre une configuration IA locale (Ollama) pour les clients on-premise sensibles à la confidentialité.

## 3. Non-objectifs (hors périmètre v1)

- Authentification LDAP/AD (prévu v2, architecture prête).
- QR codes sur les emplacements physiques.
- Gestion des prêts/retours de documents physiques.
- Application mobile native.
- Versionnement de courriers (l'app desktop ne le fait pas).
- Multi-langue (l'interface reste en français).

## 4. Utilisateurs cibles

| Rôle             | Responsabilités principales                                                                   |
|------------------|-----------------------------------------------------------------------------------------------|
| `superviseur`    | Administrateur : création de comptes, paramétrage SMTP/IMAP, configuration IA, suppression de données, audit. |
| `archiviste`     | Ingestion de documents, correction de métadonnées, gestion des emplacements physiques, administration des référentiels. |
| `agent_standard` | Réception et traitement de ses courriers imputés, recherche dans la GED, ajout de notes, réponse. |

## 5. Architecture cible

### 5.1 Déploiement hybride

Le mode est piloté par `DEPLOYMENT_MODE=saas|onprem`. Le code applicatif est identique dans les deux cas.

| Aspect                | SaaS multi-tenant                          | On-premise mono-tenant                         |
|-----------------------|--------------------------------------------|------------------------------------------------|
| Tenant                | Plusieurs, `tenant_id` partout             | `tenant_id = 1` fixe, une seule organisation   |
| Hébergement           | Render (API, Worker, PostgreSQL managé avec pgvector, Key Value Redis) + Cloudflare Pages (frontend statique) | `docker-compose up` chez le client             |
| IA                    | Anthropic Claude + Voyage AI               | Ollama + `intfloat/multilingual-e5-large`      |
| Réseau sortant        | Autorisé                                   | Peut être totalement coupé                     |

### 5.2 Monorepo

```
gedca/
├── backend/          # FastAPI + SQLAlchemy 2.0 + Alembic
├── frontend/         # React + Vite + TypeScript + Tailwind + shadcn/ui
├── worker/           # Celery (OCR, chiffrement, embeddings, watcher, IMAP)
├── docs/
│   ├── guidesoftgedca.pdf   # référence métier
│   ├── guide.txt            # extraction texte
│   ├── schema.md            # DDL PostgreSQL
│   ├── ecrans.md            # inventaire des écrans
│   └── prd/                 # ce dossier
├── docker-compose.yml
└── .env.example
```

### 5.3 Référentiel documentaire unique

Un fichier physique n'est jamais dupliqué. La table `documents` est le cœur partagé par les trois modules :

```
documents  ──────────────────────────────────────────────
    │                                                    │
ged_document (métadonnées GED)    documents_sous_dossiers (lien archivage physique)
    │
documents_courrier  (pièces jointes GEC)
courriers.document_principal_id   (pièce principale GEC)
```

### 5.4 Chiffrement des fichiers

- Algorithme : AES-256-GCM.
- Clé maître via `MASTER_KEY` (hors base).
- Clé par tenant dérivée par HKDF ; jamais stockée explicitement.
- Nom de fichier côté disque : `{checksum_sha256}.enc`.
- Texte OCR et embeddings restent en clair en base (trade-off assumé pour la recherche).

### 5.5 Pipeline d'ingestion (Celery)

Pour chaque fichier entrant (upload navigateur, watcher dossier, IMAP) :

1. `checksum_sha256` → rejet si doublon dans le tenant.
2. OCR (Tesseract `fra`) + `ocrmypdf` → PDF/A cherchable.
3. FTS : `texte_ocr` → `tsvector` config `french_unaccent`.
4. Embedding via provider IA configuré.
5. Chiffrement AES-256-GCM → déplacement vers stockage géré.
6. Création de l'enregistrement `documents` (statut `à compléter` si métadonnées manquantes).
7. Échec → file de quarantaine + notification archiviste.

### 5.6 Couche IA interchangeable

Interface unique `backend/services/ai.py` avec deux implémentations :

| Provider      | Génération                   | Embeddings                              |
|---------------|------------------------------|-----------------------------------------|
| `anthropic`   | Claude (claude-sonnet-4-6+)  | Voyage AI (`voyage-3`) ou OpenAI        |
| `ollama`      | Modèle local (Mistral/Llama) | `intfloat/multilingual-e5-large` (1024d)|

**Règle stricte** : aucune suggestion IA n'est écrite automatiquement — l'humain valide toujours.

## 6. Plan de livraison

| PRD    | Migration Alembic | Module                         | Description                                                    | Statut       |
|--------|-------------------|--------------------------------|----------------------------------------------------------------|--------------|
| PRD-00 | —                 | Vision & Architecture          | Ce document                                                    | ✅ Approuvé  |
| PRD-01 | 001               | Socle Auth & RBAC              | JWT, agents, rôles, départements, audit_log, multi-tenant      | ✅ Approuvé  |
| PRD-02 | 002               | Stockage chiffré & documents   | Upload, AES-256-GCM, déduplication SHA-256, visionneuse PDF, tables archivage (vides) | ✅ Approuvé  |
| PRD-03 | 003               | Pipeline d'ingestion           | Celery, Tesseract, ocrmypdf, embeddings, watcher, IMAP         | ✅ Approuvé  |
| PRD-04 | —                 | Module GED                     | UI dépôt, catégories, recherche FTS + sémantique               | À rédiger    |
| PRD-05 | —                 | Module Archivage physique      | Saisie hiérarchique 6 niveaux, codification dotée              | À rédiger    |
| PRD-06A| 004               | Module GEC — base              | Enregistrement, corbeilles, actions (copie, imputer, répondre, envoyer) | À rédiger    |
| PRD-06B| 005               | Module GEC — workflow          | Validation, redirection, alertes retard, statistiques          | À rédiger    |
| PRD-07 | (selon besoin)    | IA avancée                     | Classification, RAG, suggestions métadonnées                   | À rédiger    |
| PRD-08 | (selon besoin)    | Transversal production         | Tableaux de bord, exports, sauvegarde, monitoring              | À rédiger    |
| PRD-09 | —                 | Hardening sécurité             | Rate-limiting, LDAP, pentest, durcissement déploiement         | À rédiger    |

## 7. Principes directeurs

1. **Vocabulaire métier conservé** : `agents`, `correspondants`, `corbeilles`, `imputation`, `redirection`, `département`. Ne pas substituer par des termes génériques (`users`, `contacts`, `inbox`).
2. **Aucun `tenant_id` côté client** : le tenant est toujours injecté côté serveur depuis le JWT. Un endpoint qui accepte `tenant_id` en paramètre est une faille.
3. **Isolation stricte** : un test d'isolation tenant est obligatoire pour chaque nouvelle route métier.
4. **IA = suggestion uniquement** : toute valeur produite par le modèle est marquée comme telle et attend validation humaine avant écriture.
5. **Migrations Alembic versionnées** : jamais d'`ALTER TABLE` manuel. Toute modification de schéma passe par une migration nommée et réversible.
6. **Async strict** : toute route FastAPI faisant de l'I/O est `async def`. Les tâches longues (OCR, embedding, envoi mail) sont déportées vers Celery.
7. **Simplicity first** : code minimum qui résout le problème. Pas d'abstraction spéculative.

## 8. Contraintes non fonctionnelles transverses

| Axe               | Contrainte                                                                 |
|-------------------|----------------------------------------------------------------------------|
| Sécurité          | Secrets hors base (`.env`), jamais committés. OWASP Top 10 préventif.     |
| Audit             | Toute action sensible inscrit une ligne dans `audit_log`.                 |
| Tests             | Backend : `pytest`, couverture ≥ 80 % sur règles métier critiques. Frontend : Vitest + RTL. |
| Internationalisation | UI en français. Routes et codes d'erreur API en anglais standard REST. |
| Soft delete       | `supprime BOOLEAN` sur courriers et documents — jamais de suppression physique pour les entités historisables. |
| PostgreSQL 16     | Extensions requises : `pgvector`, `pg_trgm`, `unaccent`, `pgcrypto`. Configuration FTS : `french_unaccent`. |
