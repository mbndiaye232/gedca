# GEDCA — Instructions pour Claude Code

Application web de **G**estion **É**lectronique de **D**ocuments + **G**estion **É**lectronique de **C**ourriers + **A**rchivage physique. Conversion d'une application desktop WinDev existante (« SOFT GED-GEC-ARCHIVAGE » de 2S Technology) vers une stack web moderne.

## Sources de référence

- `docs/guidesoftgedca.pdf` — guide d'utilisation de l'app desktop (50 p.). **Référence métier prioritaire.**
- `docs/guide.txt` — extraction texte du guide (pour `grep` rapide).
- `bdsoftged/*.FIC` — tables HyperFile SQL de l'app desktop. **Données de test, à NE PAS migrer.** Les noms de fichiers révèlent les entités métier réelles.
- Vocabulaire à conserver dans le code et l'UI : `agents`, `correspondants`, `corbeilles`, `imputation`, `redirection`, `département`, `site/local/rayon/boîte/dossier/sous-dossier`.

Avant tout développement non trivial : relire la section du guide concernée.

## Stack technique

- **Backend** : Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2.
- **Worker asynchrone** : Celery + Redis (OCR, chiffrement, embeddings, watcher dossier, polling IMAP, envoi mails).
- **Base** : PostgreSQL 16 avec extensions `pgvector` (embeddings) et FTS native (`tsvector` config `french`). Métadonnées flexibles en `JSONB`.
- **Frontend** : React + Vite + TypeScript, Tailwind + shadcn/ui, TanStack Query, React Router, react-pdf (visionneuse).
- **Stockage fichiers** : système de fichiers serveur (chiffré au repos — voir §Chiffrement). Pas de blobs en base. Empreinte SHA-256 pour déduplication.
- **Conteneurisation** : `docker-compose.yml` à la racine pour déploiement on-premise complet (postgres + redis + api + worker + frontend nginx).

## Architecture cible

### Déploiement hybride

L'application doit pouvoir tourner dans **deux modes** identiques fonctionnellement :

1. **SaaS cloud multi-tenant** — une instance unique sert plusieurs organisations clientes. `tenant_id` présent sur toutes les tables métier. Hébergement type Render/Aiven/Cloudflare.
2. **On-premise mono-tenant** — un seul `docker-compose up` chez le client. `tenant_id = 1` fixe. Aucune fuite réseau possible si IA configurée en local.

Le mode est piloté par variable d'env `DEPLOYMENT_MODE=saas|onprem`. Le code applicatif doit rester identique ; seules la configuration et l'infrastructure changent.

### Multi-tenant

- Toutes les tables métier ont `tenant_id` (FK vers `tenants`).
- Toutes les requêtes passent par une dépendance FastAPI qui injecte le `tenant_id` de l'utilisateur authentifié.
- Aucun endpoint n'accepte un `tenant_id` en paramètre client — jamais.
- Tests obligatoires : vérifier qu'un utilisateur d'un tenant ne peut JAMAIS voir une donnée d'un autre tenant.

### Référentiel documentaire unique

```
                  ┌──────────────┐
                  │  documents   │  (fichier chiffré, OCR clair, métadonnées, embedding)
                  └──────┬───────┘
        ┌────────────────┼────────────────┐
   ged_document     courrier_piece   sous_dossier_lien
       (GED)            (GEC)           (Archivage)
```

Un même document peut être à la fois rangé dans la GED, attaché à un courrier, et lié à un sous-dossier physique. **Pas de duplication de fichier.**

## Modèle de données (entités principales)

### Socle

- `tenants` (id, code, raison_sociale, logo, smtp_host, smtp_user, smtp_password_chiffré, ai_provider, …)
- `agents` (id, tenant_id, login, password_hash, nom, prenom, email, photo, telephone, departement_id, role, actif) — vocabulaire de l'existant, pas `users`.
- `roles` : `superviseur` (= administrateur), `archiviste`, `agent_standard`.
- `departements` (id, tenant_id, libelle).
- `audit_log` (id, tenant_id, agent_id, action, entite, entite_id, payload_jsonb, ip, ts) — toute action sensible.

### Référentiels

- `correspondants` (id, tenant_id, type_id → `typeexpediteur`, raison_sociale, nom, prenom, adresse, telephone, email, …). `typeexpediteur` = `personne_physique` | `personne_morale`.
- `categories`, `thematiques`, `types_document` — taxonomies du courrier et des documents.
- `statuts_courrier`, `etats_avancement`.

### Documents (cœur)

- `documents` (id, tenant_id, titre, mime, taille_octets, checksum_sha256, chemin_stockage_chiffré, date_document, date_numerisation, categorie_id, mots_cles, resume, texte_ocr (`TEXT`), recherche_fts (`tsvector`), embedding (`vector(1024)`), metadata (`jsonb`), created_by, created_at, statut).
- `document_versions` (id, document_id, num_version, chemin_chiffré, agent_id, ts).

### Module GEC (courriers)

- `courriers` (id, tenant_id, sens `entrant|sortant|interne`, ref_externe, categorie_id, objet, date_courrier, date_arrivee, date_limite, correspondant_id, departement_destinataire_id, agent_destinataire_id, document_principal_id → documents, statut_id, mots_cles, created_by).
- `copies_courriers` (courrier_id, agent_id) — destinataires en copie.
- `imputations` (id, courrier_id, agent_imputeur_id, agent_imputé_id, instruction, ts).
- `demandes_validation` (id, courrier_id, agent_demandeur_id, agent_validateur_id, statut `en_attente|validé|rejeté`, ts_demande, ts_reponse, commentaire).
- `notes` (id, courrier_id, agent_id, contenu, ts) — post-it.
- `historiques` / `actions` (id, courrier_id, agent_id, action, payload, ts) — trace de toutes les opérations.
- `redirections` (id, agent_source_id, agent_cible_id, date_debut, date_fin, actif). Un seul actif par agent à la fois.

### Module Archivage physique — 6 niveaux

Codification dotée automatique : `SS.LL.RR.BBB.DD.SD` (Site . Local . Rayon . Boîte . Dossier . Sous-dossier).

- `sites` (id, tenant_id, numero `01..99`, libelle).
- `locaux_salles` (id, site_id, numero `01..99`, libelle).
- `rayons` (id, local_id, numero `01..99`, libelle).
- `boites` (id, rayon_id, numero `001..999`, libelle). ⚠ 3 chiffres pour la boîte.
- `dossiers_classeurs` (id, boite_id, numero `01..99`, libelle).
- `sous_dossiers` (id, dossier_id, numero `01..99`, libelle).
- `documents_sous_dossiers` (document_id, sous_dossier_id) — lien GED ↔ archivage physique.

Le code complet est calculé à la volée, pas stocké : il dérive de la hiérarchie.

## Modules — comportements clés à respecter

### GED

- Ajout : unitaire, par dossier entier (même catégorie + même sous-dossier obligatoires), depuis IMAP.
- Champs : titre, catégorie (obligatoire), fichier, date du document, mots-clés, résumé, lien sous-dossier (optionnel).
- Modification a posteriori des métadonnées toujours possible.
- Visionneuse intégrée pour PDF/images ; pour les autres types, téléchargement déchiffré temporaire.

### GEC

- Sens : `entrant`, `sortant`, `interne`. L'UI change selon le sens (correspondant requis pour entrant/sortant, pas pour interne).
- **8 corbeilles** par agent : `A traiter`, `Traités`, `En copie`, `En retard`, `A valider`, `Validés`, `A faire valider`, `En validation`.
- Coloration de la liste : noir = échéance dépassée, rouge (clair→foncé) si J-4 ou moins, vert sinon.
- **Actions disponibles** depuis « Traiter » (filtrées selon le statut) :
  - `Faire une copie` (multi-agents)
  - `Imputer` (un seul agent — **transfère la propriété**, l'imputeur passe en copie)
  - `Demander une validation` (envoie à un validateur)
  - `Notes` (post-it visible par tous les agents impliqués)
  - `Répondre` (crée un courrier sortant lié)
  - `Valider` (uniquement si en demande de validation)
  - `Envoyer` (clôture le traitement, courrier passe en « Traités »)
  - `Ajouter un document` (joindre une pièce)
  - `Consulter les notes` / `Consulter l'historique` / `Afficher les documents`
- **Redirection** : un agent en congé redirige ses courriers entrants vers un autre agent. Un seul actif par agent. Les courriers déjà en cours ne sont pas redirigés rétroactivement.
- **Alerte retard** : job quotidien qui envoie un mail aux agents dont au moins un courrier a une date limite à J-4 ou moins. Une seule alerte par courrier et par jour.
- **Statistiques** : par catégorie et par agent, sur période choisie par l'utilisateur.

### Archivage physique

- Saisie hiérarchique : on sélectionne le niveau parent pour saisir le niveau inférieur.
- Les numéros sont auto-générés, jamais saisissables par l'utilisateur.
- Bouton « Détail emplacement » qui affiche les libellés de chaque niveau (Site = …, Local = …, etc.) pour aider l'utilisateur quand le code ne suffit pas.
- Pas de QR code dans la v1 (peut venir plus tard).

## Pipeline d'ingestion

Trois voies d'entrée, toutes convergent vers le même pipeline Celery :

1. **Upload navigateur** (principal) — l'archiviste glisse-dépose ou sélectionne des fichiers depuis son poste.
2. **Dossier surveillé** — un service watchdog observe un répertoire monté côté serveur (SMB en cloud, local en on-prem) et avale tout nouveau fichier.
3. **IMAP** — polling périodique d'une boîte mail configurée par tenant, récupère les pièces jointes des messages filtrés (par date ou mots-clés).

Pour chaque fichier entrant, le worker exécute en chaîne :

1. Calcul `checksum_sha256` → rejet si doublon exact dans le tenant.
2. OCR (Tesseract `fra`) + génération PDF/A cherchable via `ocrmypdf`.
3. Extraction du texte OCR → champ `texte_ocr` (clair) + `tsvector` FR.
4. Génération de l'embedding via le provider IA configuré → champ `embedding`.
5. **Chiffrement du fichier** AES-256-GCM avec la clé du tenant → déplacement vers le stockage géré.
6. Création de l'enregistrement `documents` (statut = `à compléter` si métadonnées manquantes).
7. Échec → file de quarantaine + notification à l'archiviste.

Les archivistes corrigent et complètent les métadonnées dans l'UI après ingestion.

## Chiffrement des documents au repos

- **Algorithme** : AES-256-GCM.
- **Clé maître** : variable d'env `MASTER_KEY` (32 octets en base64), stockée hors-base.
- **Clé par tenant** : dérivée de la clé maître via HKDF avec `tenant_id` comme info — jamais stockée explicitement.
- **Chiffrement** : le fichier brut est chiffré avant écriture disque. Nom de fichier = `{checksum_sha256}.enc`. Nonce stocké en tête de fichier.
- **Déchiffrement à la volée** : la route `GET /api/documents/{id}/contenu` déchiffre en streaming pour l'utilisateur authentifié et autorisé.
- **Le texte OCR reste en clair** en base (champs `texte_ocr` et `tsvector`) pour permettre la recherche FTS. Trade-off assumé.
- **Embeddings restent en clair** pour la recherche sémantique. Idem.

## Couche IA

Sélection du provider via `AI_PROVIDER=anthropic|ollama` :

- `anthropic` (cloud SaaS) : API Claude pour classification, résumé, extraction de métadonnées ; embeddings via Voyage AI ou OpenAI.
- `ollama` (on-premise) : modèle local pour la génération de texte, embeddings via `intfloat/multilingual-e5-large`.

L'interface backend est unique (`backend/services/ai.py`), avec deux implémentations interchangeables.

**Règle stricte** : aucune métadonnée ou classification proposée par l'IA n'est écrite automatiquement. L'IA suggère, l'humain valide. Toute suggestion est marquée comme telle dans l'UI.

**Recherche** : double moteur — FTS PostgreSQL (config `french`) + similarité cosinus pgvector. Score final = combinaison pondérée des deux.

## Authentification & droits

- **v1** : comptes locaux, bcrypt + JWT.
- **v2** (à prévoir dans l'archi) : adapter LDAP/AD branchable via `AUTH_PROVIDER=local|ldap`.
- **3 rôles** : `superviseur` (= administrateur), `archiviste`, `agent_standard`.
  - Superviseur : gestion comptes, paramétrage, suppression de courriers/documents, configuration mail, supervision audit.
  - Archiviste : ingestion, correction de métadonnées, gestion des emplacements physiques, prêts/retours.
  - Agent standard : consultation, réception et traitement de ses courriers imputés, recherche, ajout de notes, réponse.
- L'accès à un courrier est dérivé du **routage par corbeilles** (un agent voit un courrier s'il est destinataire, en copie, validateur, ou redirigé). Pas d'ACL document à document.
- Pour la GED, l'accès est plus ouvert : tout agent du tenant peut rechercher dans la GED, sauf les documents marqués confidentiels (à prévoir dans `metadata.confidentiel = true`).

## Notifications email

- Un compte **SMTP par tenant** configuré par le superviseur dans l'UI (host, port, user, password chiffré en base, from).
- Trois types de mails :
  1. Notification nouveau courrier (à la création / imputation).
  2. Alerte retard (job quotidien).
  3. Notification de validation demandée / validée / rejetée.
- Option « Joindre le document » au moment de l'envoi (économie bande passante).
- Une alerte retard maximum par courrier et par jour (table `alertes_envoyees`).

## Workflow Git

**Ne jamais committer directement sur `main`.** La branche `main` est protégée.

```bash
git checkout main && git pull
git checkout -b fix/nom-du-bug         # ou feat/nom-feature
# ... modifications ...
git add <fichiers>
git commit -m "fix: description claire"
git push -u origin fix/nom-du-bug
gh pr create --title "..." --body "..."
# Merger via GitHub, pas en local
```

Conventions de branches : `fix/`, `feat/`, `refactor/`, `hotfix/`.

## Conventions de développement

- **Monorepo** : `backend/` (FastAPI), `frontend/` (React+Vite), `worker/` (Celery), `docs/`, `docker-compose.yml`.
- **Migrations Alembic** versionnées. Jamais de `ALTER TABLE` manuel.
- **Tests** :
  - Backend : `pytest`. Couverture obligatoire des règles métier critiques (corbeilles, imputation, redirection, validation) et de l'isolation tenant.
  - Frontend : Vitest + RTL.
- **Secrets** : variables d'env, jamais commitées. Fichier `.env.example` à jour.
- **Code et UI en français** (libellés, messages d'erreur, noms de routes API restent en anglais standard REST mais paramètres en français permis).
- **Audit_log** systématique pour toute action sensible.
- **Async strictement** : toute route FastAPI qui fait de l'I/O est `async def`.

## Règles de comportement (Karpathy-inspired)

### 1. Réfléchir avant de coder

- **Ne pas supposer.** Si une phrase est ambiguë, demander avant d'agir.
- Si plusieurs interprétations existent, les présenter — ne pas en choisir une silencieusement.
- Si une approche plus simple existe, la dire. Pousser en retour quand justifié.
- Si quelque chose est flou, s'arrêter, nommer ce qui prête à confusion, demander.

### 2. Simplicité d'abord

- Code minimum qui résout le problème. Rien de spéculatif.
- Pas de fonctionnalités au-delà de ce qui a été demandé.
- Pas d'abstractions pour du code à usage unique.
- Si on écrit 200 lignes et que 50 suffisent, réécrire.

### 3. Vérifier avant de toucher

- Lire les fichiers concernés avant de les modifier.
- Vérifier qu'un import supprimé n'est pas encore utilisé ailleurs.
- Tester le changement minimal avant d'étendre à tous les fichiers similaires.

### 4. Transparence sur les erreurs

- Si une modification a causé un problème, le dire et corriger immédiatement.
- Ne pas masquer une erreur dans un try/except silencieux lors du débogage.

## Plan de livraison (incrémental)

1. **Cadrage** ✅ — lecture `docs/` + `bdsoftged/`, décisions structurantes, ce `CLAUDE.md`.
2. **Socle technique** — squelette monorepo, `docker-compose.yml`, Postgres + pgvector + Redis, Alembic initial, FastAPI + auth JWT, agents/rôles/départements, audit_log, frontend Vite + auth.
3. **Stockage chiffré + table documents** — uploader simple, AES-256-GCM, déduplication SHA-256, visionneuse PDF.
4. **Pipeline d'ingestion** — Celery + Tesseract + ocrmypdf + embeddings (provider Anthropic d'abord, abstraction prête pour Ollama).
5. **Module GED** — UI dépôt, catégories, mots-clés, recherche FTS + sémantique fusionnée, modification métadonnées.
6. **Module Archivage physique** — saisie hiérarchique 6 niveaux, codification dotée, lien document ↔ sous-dossier.
7. **Module GEC** — enregistrement courrier, corbeilles, actions (faire copie, imputer, demander validation, répondre, envoyer, notes), historique, redirection, alertes retard, statistiques.
8. **IA avancée** — suggestions de classification, extraction de métadonnées, RAG sur le corpus, intégration Ollama.
9. **Transversal** — tableaux de bord, exports, sauvegarde base + sauvegarde documents (2 opérations distinctes, dossier auto-incrémenté).
10. **Hardening** — LDAP, tests de pénétration multi-tenant, documentation déploiement on-prem.

Avancer module par module, chacun avec ses tests, en validant à chaque étape.
