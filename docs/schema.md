# Schéma PostgreSQL — GEDCA

Schéma initial à traduire en migrations Alembic. Tous les noms en `snake_case`, en français quand cela correspond au vocabulaire métier de l'app desktop, en anglais sinon.

## Conventions transversales

- Toutes les clés primaires sont des `BIGSERIAL` (sauf cas justifié).
- Toutes les tables métier portent une colonne `tenant_id BIGINT NOT NULL REFERENCES tenants(id)`.
- Tous les timestamps sont `TIMESTAMPTZ` (UTC).
- Audit minimal sur tables métier : `created_at`, `created_by`, `updated_at`, `updated_by` quand pertinent.
- Soft delete : colonne `supprime BOOLEAN NOT NULL DEFAULT FALSE` plutôt que suppression physique pour les entités historisables (courriers, documents). Filtrer systématiquement.
- Mots de passe : `bcrypt`, jamais en clair, colonne `password_hash TEXT`.
- Toutes les FK ont `ON DELETE RESTRICT` par défaut, sauf liaisons faibles (`copies_courriers`, `notes`) qui peuvent être `ON DELETE CASCADE`.

## Extensions PostgreSQL requises

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid si besoin
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- recherche trigramme (libellés)
CREATE EXTENSION IF NOT EXISTS unaccent;      -- recherche sans accents
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector pour embeddings
```

Configuration FTS française avec unaccent :

```sql
CREATE TEXT SEARCH CONFIGURATION french_unaccent (COPY = french);
ALTER TEXT SEARCH CONFIGURATION french_unaccent
  ALTER MAPPING FOR hword, hword_part, word
  WITH unaccent, french_stem;
```

---

## 1. Socle multi-tenant et identités

### `tenants`

```sql
CREATE TABLE tenants (
  id              BIGSERIAL PRIMARY KEY,
  code            VARCHAR(32)  NOT NULL UNIQUE,        -- identifiant court (ex: "cour-appel-dakar")
  raison_sociale  VARCHAR(255) NOT NULL,
  adresse         TEXT,
  telephone       VARCHAR(64),
  email           VARCHAR(255),
  logo_chemin     TEXT,                                 -- chemin du logo (non chiffré)
  -- Config SMTP du tenant (mot de passe chiffré avec clé maître)
  smtp_host           VARCHAR(255),
  smtp_port           INTEGER,
  smtp_user           VARCHAR(255),
  smtp_password_enc   BYTEA,
  smtp_from           VARCHAR(255),
  smtp_use_tls        BOOLEAN DEFAULT TRUE,
  -- Config IA
  ai_provider     VARCHAR(32) NOT NULL DEFAULT 'anthropic',  -- 'anthropic' | 'ollama'
  ai_config       JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- Config alertes
  delai_alerte_jours INTEGER NOT NULL DEFAULT 4,
  -- Méta
  actif           BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `roles`

Référentiel statique, peuplé par migration de données.

```sql
CREATE TABLE roles (
  id      SMALLSERIAL PRIMARY KEY,
  code    VARCHAR(32) NOT NULL UNIQUE,   -- 'superviseur' | 'archiviste' | 'agent_standard'
  libelle VARCHAR(64) NOT NULL
);
```

### `departements`

```sql
CREATE TABLE departements (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   BIGINT NOT NULL REFERENCES tenants(id),
  code        VARCHAR(32),
  libelle     VARCHAR(255) NOT NULL,
  actif       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, libelle)
);
```

### `agents`

Nom conservé de l'app desktop (équivalent métier de `users`).

```sql
CREATE TABLE agents (
  id              BIGSERIAL PRIMARY KEY,
  tenant_id       BIGINT      NOT NULL REFERENCES tenants(id),
  login           VARCHAR(64) NOT NULL,
  password_hash   TEXT,                                  -- NULL si auth_provider='ldap'
  auth_provider   VARCHAR(16) NOT NULL DEFAULT 'local',  -- 'local' | 'ldap' (réservé v2)
  nom             VARCHAR(128) NOT NULL,
  prenom          VARCHAR(128) NOT NULL,
  email           VARCHAR(255),
  telephone       VARCHAR(64),                           -- fixe
  cellulaire      VARCHAR(64),                           -- mobile (`cel` dans la base d'origine)
  adresse         TEXT,                                  -- adresse postale (`adr` dans la base d'origine)
  photo_chemin    TEXT,                                  -- non chiffré (avatar)
  fonction        VARCHAR(128),
  departement_id  BIGINT REFERENCES departements(id),
  role_id         SMALLINT NOT NULL REFERENCES roles(id),
  actif           BOOLEAN NOT NULL DEFAULT TRUE,
  derniere_connexion TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, login),
  UNIQUE (tenant_id, email),
  CHECK (auth_provider IN ('local', 'ldap')),
  CHECK (auth_provider = 'ldap' OR password_hash IS NOT NULL)
);

CREATE INDEX idx_agents_tenant_actif ON agents (tenant_id, actif);
CREATE INDEX idx_agents_departement  ON agents (departement_id) WHERE actif;
```

### `audit_log`

Trace de toute action sensible. Append-only.

```sql
CREATE TABLE audit_log (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   BIGINT NOT NULL REFERENCES tenants(id),
  agent_id    BIGINT REFERENCES agents(id),
  action      VARCHAR(64)  NOT NULL,    -- ex: 'login', 'document.upload', 'courrier.imputer'
  entite      VARCHAR(64),               -- ex: 'documents', 'courriers'
  entite_id   BIGINT,
  payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
  ip          INET,
  user_agent  TEXT,
  ts          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_tenant_ts    ON audit_log (tenant_id, ts DESC);
CREATE INDEX idx_audit_entite       ON audit_log (entite, entite_id);
CREATE INDEX idx_audit_agent        ON audit_log (agent_id);
```

---

## 2. Référentiels métier

### `types_correspondant`

Référentiel statique (`personne_physique`, `personne_morale`).

```sql
CREATE TABLE types_correspondant (
  id      SMALLSERIAL PRIMARY KEY,
  code    VARCHAR(32) NOT NULL UNIQUE,
  libelle VARCHAR(64) NOT NULL
);
```

### `correspondants`

```sql
CREATE TABLE correspondants (
  id                  BIGSERIAL PRIMARY KEY,
  tenant_id           BIGINT NOT NULL REFERENCES tenants(id),
  type_id             SMALLINT NOT NULL REFERENCES types_correspondant(id),
  -- Personne morale
  raison_sociale      VARCHAR(255),
  -- Personne physique
  civilite            VARCHAR(16),
  nom                 VARCHAR(128),
  prenom              VARCHAR(128),
  -- Commun
  fonction            VARCHAR(128),
  adresse             TEXT,
  telephone           VARCHAR(64),
  email               VARCHAR(255),
  notes               TEXT,
  actif               BOOLEAN NOT NULL DEFAULT TRUE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (
    (type_id = 1 AND raison_sociale IS NOT NULL) OR
    (type_id = 2 AND nom IS NOT NULL)
  )
);

CREATE INDEX idx_correspondants_tenant ON correspondants (tenant_id, actif);
CREATE INDEX idx_correspondants_search ON correspondants USING gin (
  to_tsvector('french_unaccent',
    coalesce(raison_sociale,'') || ' ' || coalesce(nom,'') || ' ' || coalesce(prenom,'')
  )
);
```

### `categories`, `thematiques`, `types_document`, `statuts_courrier`, `etats_avancement`

Tous sur le même modèle :

```sql
CREATE TABLE categories (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   BIGINT NOT NULL REFERENCES tenants(id),
  libelle     VARCHAR(128) NOT NULL,
  description TEXT,
  actif       BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (tenant_id, libelle)
);

CREATE TABLE thematiques (
  id BIGSERIAL PRIMARY KEY,
  tenant_id BIGINT NOT NULL REFERENCES tenants(id),
  libelle VARCHAR(128) NOT NULL,
  actif BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (tenant_id, libelle)
);

CREATE TABLE types_document (
  id BIGSERIAL PRIMARY KEY,
  tenant_id BIGINT NOT NULL REFERENCES tenants(id),
  libelle VARCHAR(128) NOT NULL,
  UNIQUE (tenant_id, libelle)
);

-- Statuts métier des courriers (corbeilles dérivées) — référentiel statique côté code
CREATE TABLE statuts_courrier (
  id      SMALLSERIAL PRIMARY KEY,
  code    VARCHAR(32) NOT NULL UNIQUE,
  libelle VARCHAR(64) NOT NULL
);
-- Valeurs : 'a_traiter', 'traite', 'en_copie', 'a_valider', 'valide',
--          'a_faire_valider', 'en_validation', 'cloture'

CREATE TABLE etats_avancement (
  id      SMALLSERIAL PRIMARY KEY,
  code    VARCHAR(32) NOT NULL UNIQUE,
  libelle VARCHAR(64) NOT NULL
);
```

---

## 3. Documents (cœur du référentiel)

### `documents`

```sql
CREATE TABLE documents (
  id                  BIGSERIAL PRIMARY KEY,
  tenant_id           BIGINT NOT NULL REFERENCES tenants(id),
  titre               VARCHAR(512) NOT NULL,
  description         TEXT,
  resume              TEXT,
  mots_cles           TEXT,                              -- mots-clés en texte libre
  -- Classification
  categorie_id        BIGINT REFERENCES categories(id),
  thematique_id       BIGINT REFERENCES thematiques(id),
  type_document_id    BIGINT REFERENCES types_document(id),
  -- Fichier
  mime                VARCHAR(128) NOT NULL,
  taille_octets       BIGINT NOT NULL,
  checksum_sha256     CHAR(64) NOT NULL,
  chemin_stockage     TEXT NOT NULL,                     -- chemin du fichier chiffré
  nonce               BYTEA NOT NULL,                    -- nonce AES-GCM (12 octets)
  -- Dates
  date_document       DATE,                              -- date métier (souvent saisie)
  date_numerisation   TIMESTAMPTZ,
  -- OCR + recherche
  texte_ocr           TEXT,                              -- texte extrait (clair)
  recherche_fts       TSVECTOR,                          -- généré par trigger
  embedding           vector(1024),                      -- e5-large = 1024 dims (Voyage = 1024 aussi)
  -- Méta libre
  metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
  confidentiel        BOOLEAN NOT NULL DEFAULT FALSE,
  -- Provenance
  origine             VARCHAR(32) NOT NULL DEFAULT 'upload',  -- 'upload' | 'watcher' | 'imap' | 'scan'
  statut              VARCHAR(32) NOT NULL DEFAULT 'pret',    -- 'en_cours' | 'pret' | 'erreur' | 'quarantaine'
  -- Audit
  supprime            BOOLEAN NOT NULL DEFAULT FALSE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by          BIGINT REFERENCES agents(id),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_by          BIGINT REFERENCES agents(id),
  UNIQUE (tenant_id, checksum_sha256)                    -- déduplication
);

-- Index FTS + sémantique + filtres
CREATE INDEX idx_documents_fts        ON documents USING gin (recherche_fts);
CREATE INDEX idx_documents_embedding  ON documents USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_documents_tenant     ON documents (tenant_id) WHERE NOT supprime;
CREATE INDEX idx_documents_categorie  ON documents (categorie_id);
CREATE INDEX idx_documents_date_doc   ON documents (date_document);
CREATE INDEX idx_documents_metadata   ON documents USING gin (metadata);

-- Trigger d'alimentation du tsvector
CREATE OR REPLACE FUNCTION documents_fts_trigger() RETURNS trigger AS $$
BEGIN
  NEW.recherche_fts :=
    setweight(to_tsvector('french_unaccent', coalesce(NEW.titre,'')),    'A') ||
    setweight(to_tsvector('french_unaccent', coalesce(NEW.mots_cles,'')), 'B') ||
    setweight(to_tsvector('french_unaccent', coalesce(NEW.resume,'')),    'B') ||
    setweight(to_tsvector('french_unaccent', coalesce(NEW.texte_ocr,'')), 'C');
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_documents_fts
  BEFORE INSERT OR UPDATE OF titre, mots_cles, resume, texte_ocr
  ON documents
  FOR EACH ROW EXECUTE FUNCTION documents_fts_trigger();
```

### `document_versions`

```sql
CREATE TABLE document_versions (
  id              BIGSERIAL PRIMARY KEY,
  document_id     BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  num_version     INTEGER NOT NULL,
  chemin_stockage TEXT NOT NULL,
  nonce           BYTEA NOT NULL,
  checksum_sha256 CHAR(64) NOT NULL,
  taille_octets   BIGINT NOT NULL,
  commentaire     TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by      BIGINT REFERENCES agents(id),
  UNIQUE (document_id, num_version)
);
```

---

## 4. Archivage physique — 6 niveaux

Codification dotée auto : `SS.LL.RR.BBB.DD.SD`. Numéros sur `SMALLINT`, jamais saisis par l'utilisateur, attribués par séquence par parent.

```sql
CREATE TABLE sites (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   BIGINT NOT NULL REFERENCES tenants(id),
  numero      SMALLINT NOT NULL CHECK (numero BETWEEN 1 AND 99),
  libelle     VARCHAR(255) NOT NULL,
  description TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, numero)
);

CREATE TABLE locaux_salles (
  id          BIGSERIAL PRIMARY KEY,
  site_id     BIGINT NOT NULL REFERENCES sites(id) ON DELETE RESTRICT,
  numero      SMALLINT NOT NULL CHECK (numero BETWEEN 1 AND 99),
  libelle     VARCHAR(255) NOT NULL,
  description TEXT,
  UNIQUE (site_id, numero)
);

CREATE TABLE rayons (
  id          BIGSERIAL PRIMARY KEY,
  local_id    BIGINT NOT NULL REFERENCES locaux_salles(id) ON DELETE RESTRICT,
  numero      SMALLINT NOT NULL CHECK (numero BETWEEN 1 AND 99),
  libelle     VARCHAR(255) NOT NULL,
  UNIQUE (local_id, numero)
);

CREATE TABLE boites (
  id          BIGSERIAL PRIMARY KEY,
  rayon_id    BIGINT NOT NULL REFERENCES rayons(id) ON DELETE RESTRICT,
  numero      SMALLINT NOT NULL CHECK (numero BETWEEN 1 AND 999),   -- 3 chiffres
  libelle     VARCHAR(255) NOT NULL,
  UNIQUE (rayon_id, numero)
);

CREATE TABLE dossiers_classeurs (
  id          BIGSERIAL PRIMARY KEY,
  boite_id    BIGINT NOT NULL REFERENCES boites(id) ON DELETE RESTRICT,
  numero      SMALLINT NOT NULL CHECK (numero BETWEEN 1 AND 99),
  libelle     VARCHAR(255) NOT NULL,
  UNIQUE (boite_id, numero)
);

CREATE TABLE sous_dossiers (
  id          BIGSERIAL PRIMARY KEY,
  dossier_id  BIGINT NOT NULL REFERENCES dossiers_classeurs(id) ON DELETE RESTRICT,
  numero      SMALLINT NOT NULL CHECK (numero BETWEEN 1 AND 99),
  libelle     VARCHAR(255) NOT NULL,
  UNIQUE (dossier_id, numero)
);

-- Lien GED ↔ archivage physique (1 document peut être dans plusieurs sous-dossiers physiques en théorie,
-- mais en pratique généralement 0 ou 1)
CREATE TABLE documents_sous_dossiers (
  document_id    BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  sous_dossier_id BIGINT NOT NULL REFERENCES sous_dossiers(id) ON DELETE RESTRICT,
  PRIMARY KEY (document_id, sous_dossier_id)
);
```

### Vue dérivée pour les codes

Une vue calcule le code complet à la volée — jamais stocké pour éviter les désynchronisations.

```sql
CREATE VIEW v_sous_dossiers_code AS
SELECT
  sd.id AS sous_dossier_id,
  s.tenant_id,
  format('%02s.%02s.%02s.%03s.%02s.%02s',
    s.numero, l.numero, r.numero, b.numero, d.numero, sd.numero) AS code_complet,
  s.libelle  AS site,
  l.libelle  AS local,
  r.libelle  AS rayon,
  b.libelle  AS boite,
  d.libelle  AS dossier,
  sd.libelle AS sous_dossier
FROM sous_dossiers sd
JOIN dossiers_classeurs d ON d.id = sd.dossier_id
JOIN boites b              ON b.id = d.boite_id
JOIN rayons r              ON r.id = b.rayon_id
JOIN locaux_salles l       ON l.id = r.local_id
JOIN sites s               ON s.id = l.site_id;
```

---

## 5. Module GEC (courriers)

### `courriers`

```sql
CREATE TYPE sens_courrier AS ENUM ('entrant', 'sortant', 'interne');

CREATE TABLE courriers (
  id                          BIGSERIAL PRIMARY KEY,
  tenant_id                   BIGINT NOT NULL REFERENCES tenants(id),
  numero_enregistrement       VARCHAR(64),                       -- numéro interne unique tenant
  sens                        sens_courrier NOT NULL,
  ref_externe                 VARCHAR(128),                      -- référence de l'expéditeur
  categorie_id                BIGINT REFERENCES categories(id),
  objet                       TEXT NOT NULL,
  mots_cles                   TEXT,
  -- Dates
  date_courrier               DATE,
  date_arrivee                DATE,
  date_limite                 DATE,
  -- Correspondant (entrant/sortant uniquement)
  correspondant_id            BIGINT REFERENCES correspondants(id),
  -- Destinataire interne
  departement_destinataire_id BIGINT REFERENCES departements(id),
  agent_destinataire_id       BIGINT REFERENCES agents(id),
  -- Pièce principale
  document_principal_id       BIGINT REFERENCES documents(id),
  -- Workflow
  statut_id                   SMALLINT NOT NULL REFERENCES statuts_courrier(id),
  agent_proprietaire_id       BIGINT REFERENCES agents(id),     -- agent qui « porte » le courrier (change après imputation)
  -- Réponse / chaînage
  courrier_origine_id         BIGINT REFERENCES courriers(id),   -- si c'est une réponse
  -- Audit
  supprime                    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by                  BIGINT REFERENCES agents(id),
  updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, numero_enregistrement)
);

CREATE INDEX idx_courriers_tenant_proprio ON courriers (tenant_id, agent_proprietaire_id) WHERE NOT supprime;
CREATE INDEX idx_courriers_statut         ON courriers (tenant_id, statut_id) WHERE NOT supprime;
CREATE INDEX idx_courriers_date_limite    ON courriers (date_limite) WHERE date_limite IS NOT NULL AND NOT supprime;
CREATE INDEX idx_courriers_search         ON courriers USING gin (
  to_tsvector('french_unaccent', coalesce(objet,'') || ' ' || coalesce(mots_cles,''))
);
```

### `copies_courriers`

```sql
CREATE TABLE copies_courriers (
  courrier_id BIGINT NOT NULL REFERENCES courriers(id) ON DELETE CASCADE,
  agent_id    BIGINT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  lu          BOOLEAN NOT NULL DEFAULT FALSE,
  ajoute_par  BIGINT REFERENCES agents(id),
  ajoute_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (courrier_id, agent_id)
);

CREATE INDEX idx_copies_agent ON copies_courriers (agent_id);
```

### `imputations`

Historique des transferts de propriété.

```sql
CREATE TABLE imputations (
  id                  BIGSERIAL PRIMARY KEY,
  courrier_id         BIGINT NOT NULL REFERENCES courriers(id) ON DELETE CASCADE,
  agent_imputeur_id   BIGINT NOT NULL REFERENCES agents(id),
  agent_impute_id     BIGINT NOT NULL REFERENCES agents(id),
  instruction         TEXT,
  ts                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_imputations_courrier ON imputations (courrier_id, ts DESC);
```

### `demandes_validation`

```sql
CREATE TYPE statut_validation AS ENUM ('en_attente', 'valide', 'rejete');

CREATE TABLE demandes_validation (
  id                  BIGSERIAL PRIMARY KEY,
  courrier_id         BIGINT NOT NULL REFERENCES courriers(id) ON DELETE CASCADE,
  agent_demandeur_id  BIGINT NOT NULL REFERENCES agents(id),
  agent_validateur_id BIGINT NOT NULL REFERENCES agents(id),
  statut              statut_validation NOT NULL DEFAULT 'en_attente',
  commentaire         TEXT,
  ts_demande          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ts_reponse          TIMESTAMPTZ
);

CREATE INDEX idx_validation_validateur ON demandes_validation (agent_validateur_id, statut);
```

### `notes_courrier`

Post-it électroniques.

```sql
CREATE TABLE notes_courrier (
  id          BIGSERIAL PRIMARY KEY,
  courrier_id BIGINT NOT NULL REFERENCES courriers(id) ON DELETE CASCADE,
  agent_id    BIGINT NOT NULL REFERENCES agents(id),
  contenu     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notes_courrier ON notes_courrier (courrier_id, created_at);
```

### `historiques_courrier`

Append-only, distinct de `audit_log` (utilisé pour l'affichage utilisateur de l'historique d'un courrier).

```sql
CREATE TABLE historiques_courrier (
  id          BIGSERIAL PRIMARY KEY,
  courrier_id BIGINT NOT NULL REFERENCES courriers(id) ON DELETE CASCADE,
  agent_id    BIGINT REFERENCES agents(id),
  action      VARCHAR(64) NOT NULL,    -- 'creation','imputation','copie','reponse','validation_demandee','validation','envoi','note',...
  payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
  ts          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_histo_courrier ON historiques_courrier (courrier_id, ts DESC);
```

### `documents_courrier`

Pièces jointes additionnelles (la pièce principale est `courriers.document_principal_id`).

```sql
CREATE TABLE documents_courrier (
  courrier_id BIGINT NOT NULL REFERENCES courriers(id) ON DELETE CASCADE,
  document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
  ajoute_par  BIGINT REFERENCES agents(id),
  ajoute_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (courrier_id, document_id)
);
```

### `redirections`

Un seul actif par agent à la fois, garanti par index partiel unique.

```sql
CREATE TABLE redirections (
  id                BIGSERIAL PRIMARY KEY,
  tenant_id         BIGINT NOT NULL REFERENCES tenants(id),
  agent_source_id   BIGINT NOT NULL REFERENCES agents(id),
  agent_cible_id    BIGINT NOT NULL REFERENCES agents(id),
  date_debut        DATE NOT NULL DEFAULT CURRENT_DATE,
  date_fin          DATE,
  actif             BOOLEAN NOT NULL DEFAULT TRUE,
  motif             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (agent_source_id <> agent_cible_id)
);

CREATE UNIQUE INDEX uniq_redirection_active
  ON redirections (agent_source_id) WHERE actif;

CREATE INDEX idx_redirections_cible ON redirections (agent_cible_id) WHERE actif;
```

### `alertes_envoyees`

Garantit « une alerte par courrier par jour » au plus.

```sql
CREATE TABLE alertes_envoyees (
  id              BIGSERIAL PRIMARY KEY,
  courrier_id     BIGINT NOT NULL REFERENCES courriers(id) ON DELETE CASCADE,
  agent_id        BIGINT NOT NULL REFERENCES agents(id),
  type_alerte     VARCHAR(32) NOT NULL,  -- 'retard', 'nouveau', 'validation_demandee', ...
  date_envoi      DATE NOT NULL DEFAULT CURRENT_DATE,
  ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (courrier_id, agent_id, type_alerte, date_envoi)
);
```

---

## 6. Vues utilitaires — corbeilles dérivées

Plutôt que de matérialiser les 8 corbeilles, on les dérive d'une vue paramétrée par agent. Exemple :

```sql
-- Helper : courriers visibles par un agent (titulaire OU en copie)
CREATE VIEW v_courriers_agent AS
SELECT c.*, ag.id AS agent_id, 'proprietaire' AS role_vis
FROM courriers c
JOIN agents ag ON ag.id = c.agent_proprietaire_id
WHERE NOT c.supprime
UNION ALL
SELECT c.*, cc.agent_id, 'copie' AS role_vis
FROM courriers c
JOIN copies_courriers cc ON cc.courrier_id = c.id
WHERE NOT c.supprime;
```

Les corbeilles sont des `SELECT` filtrés sur cette vue + jointure `statuts_courrier` + jointure `demandes_validation` selon le cas. Le détail des règles ira dans `backend/services/corbeilles.py` plutôt qu'en SQL pur.

---

## 7. Sauvegardes

Pas de table dédiée. La table `audit_log` enregistre les opérations de sauvegarde via les `action='sauvegarde.base'` et `action='sauvegarde.documents'`. Le dossier cible est un paramètre côté worker.

---

## 8. Ordre des migrations Alembic

Les migrations sont alignées sur le découpage en PRD. Chaque migration est nommée `NNN_objet.py` (`001_socle.py`, `002_stockage.py`, etc.).

### Migration 001 — Socle (PRD-01)
1. Extensions PostgreSQL (`pgcrypto`, `pg_trgm`, `unaccent`, `vector`) + configuration FTS `french_unaccent`.
2. Référentiels statiques : `roles`, `types_correspondant`.
3. `tenants`.
4. `departements`, `agents` (version initiale sans `cellulaire` ni `adresse`).
5. `audit_log`.
6. Seed : rôles, types correspondant.

### Migration 002 — Compléments PRD-01 (alignement base d'origine)
7. `ALTER TABLE agents` : ajout de `cellulaire VARCHAR(64)` et `adresse TEXT` (cf. `docs/reconciliation-bdsoftged.md`).

### Migration 003 — Stockage et archivage physique (PRD-02)
8. `categories`, `thematiques`, `types_document`, `correspondants`.
9. `documents`, `document_versions`, trigger FTS.
10. **Archivage physique** (toutes les tables, vides — peuplées au runtime par PRD-05) :
    `sites` → `locaux_salles` → `rayons` → `boites` → `dossiers_classeurs` → `sous_dossiers` → `documents_sous_dossiers` + vue `v_sous_dossiers_code`.

> **Choix** : créer les 6 tables d'archivage dès cette migration permet à `documents_sous_dossiers` d'avoir une FK propre sans `DEFERRABLE`. PRD-05 n'ajoute aucune migration de schéma, juste les routes et l'UI.

### Migration 004 — Pipeline ingestion (PRD-03)
11. `ALTER TABLE tenants` — ajout des colonnes IMAP (`imap_host`, `imap_port`, `imap_user`, `imap_password_enc`, `imap_folder`, `imap_actif`, `imap_dernier_uid`).
12. `imap_pieces_jointes` — métadonnées des pièces jointes en attente d'intégration (le contenu binaire est stocké sur disque chiffré, pas en base — voir PRD-03 §5.8).
13. `statuts_courrier`, `etats_avancement` — référentiels (créés ici car référencés par GEC ensuite).

### Migration 005 — GEC (PRD-06)
14. `courriers`, `copies_courriers`, `imputations`, `demandes_validation`, `notes_courrier`, `historiques_courrier`, `documents_courrier`, `redirections`, `alertes_envoyees`.
15. Vues utilitaires : `v_courriers_agent`.

### Migrations ultérieures
- PRD-07 (IA avancée) : éventuelles tables de suggestions / cache.
- PRD-08 (Transverse) : tables de sauvegarde, exports.

---

## 9. Points laissés ouverts

- **Recherche FTS sur correspondants** : pour l'instant un index GIN ponctuel ; à transformer en colonne `tsvector` matérialisée si la volumétrie l'exige.
- **Versionnement des courriers** : pas prévu en v1 (l'app desktop ne le fait pas).
- **Prêts/retours physiques** : pas dans l'app desktop d'origine ; à ne pas ajouter en v1.
- **Suppression cascade des documents** : volontairement `ON DELETE RESTRICT`. Un document lié à un courrier ou un sous-dossier ne peut pas être supprimé tant que le lien existe. Le superviseur doit nettoyer les liens d'abord.
- **`document_principal_id` peut être NULL** sur courriers internes brefs sans pièce jointe. À confirmer côté UI.
