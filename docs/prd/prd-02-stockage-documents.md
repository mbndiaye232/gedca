# PRD-02 — Stockage chiffré & Documents

| Champ        | Valeur                                                          |
|--------------|-----------------------------------------------------------------|
| **ID**       | PRD-02                                                          |
| **Module**   | Stockage / Documents                                            |
| **Statut**   | Approuvé                                                        |
| **Auteur**   | mbndiaye232                                                     |
| **Date**     | 2026-05-31                                                      |
| **Dépend de**| PRD-01 (Auth & RBAC — JWT, tenant_id, agents)                   |

---

## 1. Contexte & problème

Le guide (§ III. Documents) décrit un système où les documents sont chiffrés dès leur dépôt : *« ils sont cryptés par l'application lors de leur enregistrement et le document source est supprimé »*. Un utilisateur qui ouvre le fichier en dehors de l'application voit un contenu inintelligible. Quand un utilisateur autorisé demande la consultation, l'application déchiffre et ouvre ; *« à la fermeture, le fichier décrypté est supprimé »*.

GEDCA doit respecter cette garantie tout en ajoutant la déduplication par empreinte SHA-256 et la visionneuse PDF inline. Ce PRD pose la couche de stockage sur laquelle s'appuient le pipeline OCR (PRD-03) et le module GED (PRD-04).

## 2. Objectifs

- OBJ-1 : Chiffrement AES-256-GCM systématique de tout fichier déposé, avec clé dérivée par tenant (HKDF).
- OBJ-2 : Déduplication par empreinte SHA-256 — un même fichier n'est jamais stocké deux fois dans un tenant.
- OBJ-3 : Upload unitaire synchrone avec saisie de métadonnées de base (titre, catégorie obligatoire, mots-clés, résumé, date du document, lien emplacement physique optionnel).
- OBJ-4 : Déchiffrement à la volée en streaming pour la consultation — aucun fichier déchiffré permanent sur disque.
- OBJ-5 : Visionneuse PDF inline (react-pdf) pour les PDF ; téléchargement temporaire sécurisé pour les autres formats.
- OBJ-6 : Versionnement du fichier physique : remplacer le fichier d'un document conserve l'historique des versions.
- OBJ-7 : Référentiels `categories`, `thematiques`, `types_document` gérés par le superviseur.

## 3. Non-objectifs (hors périmètre)

- OCR Tesseract et génération d'embeddings → PRD-03 (Pipeline d'ingestion).
- Upload par lot depuis un dossier → PRD-03 (watcher Celery).
- Intégration IMAP → PRD-03.
- Recherche FTS + sémantique → PRD-04 (Module GED).
- Suggestions IA de classification → PRD-07.
- Prêts/retours de documents physiques (hors scope v1).
- QR codes (hors scope v1).

## 4. Utilisateurs cibles

| Rôle             | Ce qu'ils font dans ce module                                             |
|------------------|---------------------------------------------------------------------------|
| `superviseur`    | Gère les référentiels (catégories, thématiques, types). Supprime des documents. |
| `archiviste`     | Dépose des documents, saisit et corrige les métadonnées, gère les liens d'emplacement physique. |
| `agent_standard` | Consulte les documents auxquels il a accès, ouvre la visionneuse. Ne peut pas supprimer. |

## 5. Fonctionnalités

### 5.1 Service de chiffrement (`backend/services/crypto.py`) — technique

**Description :** Toutes les opérations de chiffrement/déchiffrement passent par ce service. Aucune route ne manipule les clés directement.

**Règles métier :**
- RG-1 : La clé maître est lue depuis la variable d'environnement `MASTER_KEY` (32 octets encodés en base64). Elle n'est jamais stockée en base.
- RG-2 : La clé par tenant est dérivée par HKDF-SHA-256 :
  `tenant_key = HKDF(master_key, salt=b"", info=b"gedca-doc-" + str(tenant_id).encode(), length=32)`
- RG-3 : Chaque fichier est chiffré avec AES-256-GCM. Un nonce de 12 octets aléatoires est généré par fichier.
- RG-4 : Format sur disque : `nonce (12 octets) || ciphertext || auth_tag (16 octets)`.
- RG-5 : Nom de fichier sur disque : `{checksum_sha256}.enc`.
- RG-6 : Chemin de stockage : `{STORAGE_ROOT}/{tenant_id}/{checksum_sha256}.enc`.
- RG-7 : La colonne `documents.nonce` (BYTEA 12 octets) est la source de vérité pour le déchiffrement — elle est lue depuis le début du fichier mais aussi stockée en base pour validation.
- RG-8 : Le déchiffrement est réalisé en streaming par chunks de 64 Ko pour limiter l'empreinte mémoire sur les gros fichiers.
- RG-9 : Si `MASTER_KEY` est absente au démarrage, l'application refuse de démarrer (vérification dans `lifespan`).

---

### 5.2 Upload d'un document (écran 2.1 — 🔴 P0)

**Description :** Un archiviste (ou superviseur) dépose un fichier depuis son navigateur et saisit les métadonnées.

**Règles métier :**
- RG-1 : La catégorie est **obligatoire**. Tout upload sans catégorie retourne HTTP 422.
- RG-2 : Le titre est obligatoire.
- RG-3 : Tout type de fichier est accepté (PDF, JPEG, PNG, TIFF, DOCX, XLSX, etc.). La détection du type MIME est faite côté serveur avec `python-magic` — la valeur fournie par le client est ignorée.
- RG-4 : Taille maximale configurable via `MAX_UPLOAD_SIZE_MB` (défaut : 100 Mo). Dépassement → HTTP 413.
- RG-5 : Le checksum SHA-256 est calculé côté serveur sur le fichier reçu avant toute opération.
- RG-6 : **Déduplication** — si `(tenant_id, checksum_sha256)` existe déjà en base et que le document n'est pas supprimé (`supprime = FALSE`) : retourner HTTP 409 avec le champ `document_id` existant et un message explicite *« Ce fichier est déjà présent (document #N). »*.
- RG-7 : Le fichier est chiffré (voir 5.1) et déplacé vers `STORAGE_ROOT`. Le fichier temporaire reçu est supprimé.
- RG-8 : L'enregistrement `documents` est créé avec `statut='pret'`, `origine='upload'`.
- RG-9 : `date_numerisation` est renseignée automatiquement à l'heure de l'upload.
- RG-10 : Si un `sous_dossier_id` est fourni, une entrée est créée dans `documents_sous_dossiers`.
- RG-11 : L'action `document.upload` est inscrite dans `audit_log`.

**Comportement attendu (UI) :**
1. L'utilisateur glisse-dépose ou sélectionne un fichier. Le nom de fichier et le poids sont affichés.
2. Il saisit le titre (pré-rempli avec le nom du fichier sans extension, modifiable), choisit la catégorie (combo + bouton « + » pour créer à la volée), entre mots-clés, résumé, date du document.
3. Il peut cocher « Document physique associé » → le sélecteur d'emplacement (composant 3.7 de `ecrans.md`) s'affiche en modal.
4. Il clique « Valider ». Une barre de progression s'affiche pendant l'upload.
5. En cas de doublon, un bandeau d'avertissement propose un lien vers le document existant.
6. En cas de succès, redirection vers la fiche du document créé.

**Champs / données :** `documents.titre`, `categorie_id` (obligatoire), `thematique_id`, `type_document_id`, `fichier` (multipart), `date_document`, `mots_cles`, `resume`, `confidentiel`, `description`, `sous_dossier_id` (optionnel).

---

### 5.3 Streaming déchiffré — consultation (technique)

**Description :** Route `GET /api/documents/{id}/contenu` qui déchiffre le fichier et le retourne en streaming. Utilisée par la visionneuse (5.4) et le téléchargement (5.5).

**Règles métier :**
- RG-1 : Vérifier que le document appartient au tenant de l'agent connecté.
- RG-2 : Vérifier que `supprime = FALSE` et `statut != 'quarantaine'`.
- RG-3 : Pour les documents `confidentiel = TRUE`, seuls les agents avec rôle `archiviste` ou `superviseur` peuvent accéder au contenu. Un `agent_standard` reçoit HTTP 403.
- RG-4 : La réponse est un `StreamingResponse` avec `Content-Type` issu de `documents.mime` et `Content-Disposition` selon le mode (`inline` pour PDF/images, `attachment` pour les autres).
- RG-5 : Aucun fichier déchiffré n'est écrit sur disque. Le déchiffrement est entièrement en mémoire / streaming.
- RG-6 : L'accès est loggué dans `audit_log` (action `document.consulter`) — une seule fois par session utilisateur par document (TTL 30 min en cache Redis pour éviter le bruit dans les logs lors de la pagination de la visionneuse).

---

### 5.4 Visionneuse de document (écran 2.6 — 🔴 P0)

**Description :** Affichage intégré dans l'interface selon le type de fichier.

**Règles métier :**
- RG-1 : **PDF** — rendu inline via `react-pdf` (`pdfjs-dist`). La bibliothèque consomme le stream de `GET /api/documents/{id}/contenu`. Navigation page à page, zoom.
- RG-2 : **Images** (JPEG, PNG, TIFF, WEBP, GIF) — affichage inline dans une balise `<img>`.
- RG-3 : **Autres formats** (DOCX, XLSX, ODT, etc.) — le fichier déchiffré est téléchargé par le navigateur avec `Content-Disposition: attachment`. L'utilisateur l'ouvre localement avec son application.
- RG-4 : La visionneuse est présentée dans un modal. À la fermeture du modal, aucune action serveur n'est requise (pas de fichier temporaire côté serveur — voir RG-5 de 5.3).
- RG-5 : Le titre du document est affiché dans le header du modal.

---

### 5.5 Modification des métadonnées (écran 2.4 — 🟠 P1)

**Description :** Un archiviste ou superviseur corrige les métadonnées d'un document existant. Autorisé aussi par l'auteur (`created_by`).

**Règles métier :**
- RG-1 : Champs modifiables : titre, catégorie, thématique, type, mots-clés, résumé, date du document, description, confidentiel, lien emplacement physique (`documents_sous_dossiers`).
- RG-2 : Remplacer le fichier physique (upload d'un nouveau fichier) crée automatiquement une version (voir 5.6). Ce n'est pas obligatoire — les métadonnées peuvent être modifiées sans changer le fichier.
- RG-3 : Seul un `superviseur` peut modifier le champ `confidentiel`.
- RG-4 : Toute modification inscrit `document.update` dans `audit_log` avec le diff des champs modifiés en payload JSONB.
- RG-5 : `updated_at` et `updated_by` sont mis à jour.

---

### 5.6 Versionnement du fichier physique

**Description :** Quand un archiviste ou superviseur remplace le fichier d'un document existant, l'ancienne version est conservée dans `document_versions`.

**Règles métier :**
- RG-1 : Avant de remplacer, l'enregistrement courant (`chemin_stockage`, `nonce`, `checksum_sha256`, `taille_octets`) est copié dans `document_versions` avec `num_version` = dernier `num_version + 1` (ou 1 si c'est la première version archivée).
- RG-2 : La table `documents` est mise à jour avec les données du nouveau fichier.
- RG-3 : Le fichier physique de l'ancienne version est conservé sur disque (sous son `checksum_sha256.enc`). Il n'est pas supprimé automatiquement.
- RG-4 : L'UI (écran 2.4) affiche la liste des versions passées avec date et auteur. Pas de restauration automatique en v1 — information seule.
- RG-5 : Si le nouveau fichier a le même checksum que la version actuelle, aucune version n'est créée (idempotent).

---

### 5.7 Lien emplacement physique (`documents_sous_dossiers`)

**Description :** Un document peut être associé à un sous-dossier d'archivage physique. Ce lien est optionnel et modifiable après création.

**Règles métier :**
- RG-1 : Un document peut être lié à 0 ou 1 sous-dossier en pratique (le guide implique généralement un seul emplacement physique). La table permet N liens mais l'UI gère 1 lien par défaut.
- RG-2 : Le sous-dossier doit appartenir au même tenant.
- RG-3 : La suppression du lien ne supprime ni le document ni le sous-dossier.
- RG-4 : Un document lié à un sous-dossier ne peut pas être physiquement supprimé tant que le lien existe (contrainte `ON DELETE RESTRICT` en base). Le superviseur doit d'abord supprimer le lien.

---

### 5.8 Détail emplacement physique (écran 2.7 — 🟠 P1)

**Description :** Modal lecture seule affichant les libellés complets de la hiérarchie d'archivage physique pour un document donné.

**Règles métier :**
- RG-1 : Affiche les 6 niveaux : Site, Local, Rayon, Boîte, Dossier, Sous-dossier avec code (`SS.LL.RR.BBB.DD.SD`) et libellé pour chaque niveau.
- RG-2 : Utilise la vue `v_sous_dossiers_code` (définie dans `docs/schema.md` §4).
- RG-3 : Si le document n'a pas d'emplacement physique, afficher *« Aucun emplacement physique associé »*.
- RG-4 : Accessible depuis la liste des documents et depuis la fiche de modification.

---

### 5.9 Suppression d'un document (écran 2.8 — 🟡 P2)

**Description :** Seul le superviseur peut supprimer un document.

**Règles métier :**
- RG-1 : La suppression est un **soft delete** (`supprime = TRUE`). Le fichier physique chiffré est conservé sur disque.
- RG-2 : Avant de marquer `supprime = TRUE`, vérifier :
  - Aucun courrier ne référence ce document via `courriers.document_principal_id` ou `documents_courrier`.
  - Aucun lien `documents_sous_dossiers` actif.
  - Si une contrainte empêche la suppression → HTTP 409 avec message précisant le blocage (*« Ce document est lié au courrier #N »*).
- RG-3 : Une confirmation explicite est demandée à l'UI avant envoi de la requête.
- RG-4 : L'action `document.supprimer` est inscrite dans `audit_log`.
- RG-5 : Les documents supprimés n'apparaissent plus dans les résultats de recherche ni dans les visionneuses.

---

### 5.10 Référentiels : catégories, thématiques, types de document (écran 4.8 — 🟡 P2)

**Description :** Le superviseur gère les listes de valeurs utilisées dans les formulaires de documents et de courriers.

**Règles métier :**
- RG-1 : Les trois référentiels (`categories`, `thematiques`, `types_document`) sont gérés par tenant.
- RG-2 : Un archiviste peut créer une catégorie **à la volée** depuis le formulaire d'upload (bouton « + » inline), sans passer par l'écran d'administration.
- RG-3 : Libellé unique par tenant pour chaque référentiel (contrainte en base).
- RG-4 : Désactiver (`actif = FALSE`) plutôt que supprimer si des documents y sont liés.
- RG-5 : Les référentiels sont communs à la GED et au module GEC (une même catégorie peut qualifier un document et un courrier).

---

## 6. Critères d'acceptation

| ID    | Critère                                                                                                          | Type   |
|-------|------------------------------------------------------------------------------------------------------------------|--------|
| CA-01 | Upload d'un fichier PDF : le fichier est chiffré sur disque (contenu binaire non lisible), enregistrement en base créé. | Pytest |
| CA-02 | Déduplication : uploader deux fois le même fichier retourne HTTP 409 avec `document_id` de l'existant.           | Pytest |
| CA-03 | Deux fichiers identiques uploadés dans deux tenants différents → deux enregistrements distincts (isolation).     | Pytest |
| CA-04 | `GET /api/documents/{id}/contenu` retourne les octets déchiffrés identiques au fichier original.                | Pytest |
| CA-05 | `GET /api/documents/{id}/contenu` par un agent d'un autre tenant → HTTP 404 (pas de fuite d'existence).         | Pytest |
| CA-06 | Document `confidentiel = TRUE` : un `agent_standard` reçoit HTTP 403 sur `/contenu`.                             | Pytest |
| CA-07 | Catégorie absente à l'upload → HTTP 422.                                                                         | Pytest |
| CA-08 | Fichier > `MAX_UPLOAD_SIZE_MB` → HTTP 413.                                                                       | Pytest |
| CA-09 | MIME type fourni par le client ignoré : un PNG renommé `.pdf` est détecté comme `image/png` côté serveur.       | Pytest |
| CA-10 | Remplacement du fichier : version précédente dans `document_versions`, nouveau `checksum_sha256` dans `documents`. | Pytest |
| CA-11 | Même checksum à l'upload de remplacement → aucune entrée `document_versions` créée.                             | Pytest |
| CA-12 | Suppression d'un document lié à un courrier → HTTP 409 avec message.                                            | Pytest |
| CA-13 | Suppression valide → `supprime = TRUE`, document absent des résultats de recherche.                              | Pytest |
| CA-14 | `audit_log` contient `document.upload` après chaque upload réussi.                                              | Pytest |
| CA-15 | Démarrage sans `MASTER_KEY` → l'application refuse de démarrer avec message d'erreur clair.                     | Pytest |
| CA-16 | UI — Visionneuse : un PDF s'affiche inline dans le modal (react-pdf), navigation page OK.                        | Manuel |
| CA-17 | UI — Visionneuse : un DOCX déclenche un téléchargement navigateur.                                              | Manuel |
| CA-18 | UI — Upload avec doublon : bandeau d'avertissement avec lien vers le document existant.                          | Manuel |
| CA-19 | UI — Détail emplacement physique : les 6 niveaux s'affichent avec code et libellé.                              | Manuel |
| CA-20 | UI — Catégorie créée à la volée dans le formulaire d'upload : disponible immédiatement dans le combo.           | Manuel |

## 7. Contraintes techniques

- **Chiffrement** : `cryptography` (Python). Pas de `pycryptodome` ou autre.
- **MIME detection** : `python-magic` (libmagic). Jamais `mimetypes.guess_type` seul (trop facilement trompé).
- **Streaming** : `StreamingResponse` FastAPI avec générateur Python. Chunks de 64 Ko. L'intégralité du fichier déchiffré ne doit jamais résider en RAM simultanément.
- **Taille max** : configurée côté nginx (`client_max_body_size`) ET côté FastAPI (`UploadFile` + vérification explicite) pour un double filet.
- **Stockage** : `STORAGE_ROOT` est une variable d'env pointant sur un volume persistant. En SaaS, ce volume est un FS réseau (NFS/S3FS). En on-prem, c'est un répertoire local monté dans le conteneur.
- **Pas de blob en base** : les fichiers ne sont jamais stockés dans PostgreSQL. Seul le chemin est en base.
- **Multi-tenant** : toutes les requêtes filtrent sur `tenant_id` extrait du JWT. La clé de chiffrement est différente par tenant (HKDF).
- **Async** : toutes les routes FastAPI sont `async def`. La lecture/écriture de fichiers utilise `aiofiles`.
- **Audit** : `document.upload`, `document.consulter`, `document.update`, `document.supprimer` dans `audit_log`.

## 8. API endpoints

| Méthode | Route                                     | Rôles autorisés                    | Description                                              |
|---------|-------------------------------------------|------------------------------------|----------------------------------------------------------|
| POST    | `/api/documents`                          | archiviste, superviseur            | Upload d'un document (multipart/form-data)               |
| GET     | `/api/documents/{id}`                     | Tout agent connecté                | Métadonnées du document                                  |
| PUT     | `/api/documents/{id}`                     | archiviste, superviseur, créateur  | Modifier les métadonnées (et/ou remplacer le fichier)    |
| DELETE  | `/api/documents/{id}`                     | superviseur                        | Soft delete                                              |
| GET     | `/api/documents/{id}/contenu`             | Tout agent connecté (cf. RG confidentialité) | Streaming déchiffré                          |
| GET     | `/api/documents/{id}/versions`            | archiviste, superviseur            | Liste des versions passées                               |
| POST    | `/api/documents/{id}/emplacement`         | archiviste, superviseur            | Lier à un sous-dossier physique                          |
| DELETE  | `/api/documents/{id}/emplacement/{sdid}`  | archiviste, superviseur            | Supprimer le lien emplacement physique                   |
| GET     | `/api/categories`                         | Tout agent connecté                | Lister les catégories du tenant                          |
| POST    | `/api/categories`                         | archiviste, superviseur            | Créer une catégorie (y compris à la volée)               |
| PUT     | `/api/categories/{id}`                    | superviseur                        | Modifier / désactiver                                    |
| GET     | `/api/thematiques`                        | Tout agent connecté                | Lister les thématiques                                   |
| POST    | `/api/thematiques`                        | superviseur                        | Créer                                                    |
| GET     | `/api/types-document`                     | Tout agent connecté                | Lister les types de document                             |
| POST    | `/api/types-document`                     | superviseur                        | Créer                                                    |

## 9. Modèle de données impacté

Tables créées dans la **migration Alembic 002** (DDL complet dans `docs/schema.md`) :

- `categories` — référentiel par tenant (libellé unique).
- `thematiques` — référentiel par tenant.
- `types_document` — référentiel par tenant.
- `documents` — table centrale ; colonnes `texte_ocr`, `recherche_fts`, `embedding` créées mais laissées à `NULL` jusqu'à PRD-03. Trigger FTS `trg_documents_fts` créé (indexe titre/mots_cles/resume dès maintenant, `texte_ocr` sera alimenté par PRD-03).
- `document_versions` — historique des versions physiques.
- **Toutes les tables d'archivage physique** (vides) : `sites`, `locaux_salles`, `rayons`, `boites`, `dossiers_classeurs`, `sous_dossiers`, plus la vue `v_sous_dossiers_code`. Décidé en cadrage Phase A : créer le squelette dès la migration 002 permet une FK directe sur `documents_sous_dossiers` sans `DEFERRABLE`. PRD-05 n'ajoutera aucune table — il pose seulement les routes, l'UI et le sélecteur réutilisable.
- `documents_sous_dossiers` — lien GED ↔ archivage physique (table de liaison).

> **Note** : les tables d'archivage sont créées vides dans cette migration. Les premières lignes ne pourront être insérées qu'avec les routes et l'UI livrées en PRD-05. Le lien `documents_sous_dossiers` est exposé via les routes `POST/DELETE /api/documents/{id}/emplacement` dès PRD-02 ; il restera factuellement inutilisable tant qu'aucun sous-dossier n'existe en base.

Variables d'environnement nouvelles à documenter dans `.env.example` :

```
MASTER_KEY=<32 octets en base64 — généré par openssl rand -base64 32>
STORAGE_ROOT=/var/gedca/storage
MAX_UPLOAD_SIZE_MB=100
```

## 10. Dépendances inter-modules

- Requiert : PRD-01 (JWT, `tenant_id`, `agents`, `departements` déjà en base).
- Requiert (faiblement) : PRD-05 pour créer des liens d'emplacement physique (FK existera, données pas encore).
- Requis par :
  - PRD-03 (Pipeline) : réutilise le service crypto et la table `documents` ; ajoute `texte_ocr` / `embedding` via Celery.
  - PRD-04 (GED) : construit la recherche FTS + sémantique sur cette fondation.
  - PRD-06 (GEC) : `courriers.document_principal_id` et `documents_courrier` référencent `documents`.

## 11. Risques & points ouverts

| Risque / Question ouverte                                          | Probabilité | Impact | Mitigation / décision                                                                      |
|--------------------------------------------------------------------|-------------|--------|--------------------------------------------------------------------------------------------|
| Rotation de `MASTER_KEY` invalide tous les fichiers chiffrés       | Faible      | Critique | Documenter la procédure de re-chiffrement. Pas de rotation automatique en v1.             |
| Fichier `.enc` orphelin si le process crash après écriture disque mais avant commit DB | Faible | Moyen | Job de réconciliation périodique (scan du disque vs base) — à inclure dans PRD-03/08.     |
| Volume de stockage non borné en SaaS                               | Moyenne     | Moyen  | Colonne `metadata.quota_mo` sur `tenants` à prévoir ; alertes superviseur. Pas en v1.     |
| `python-magic` non disponible sur toutes les images Docker         | Faible      | Faible | Inclure `libmagic1` dans `Dockerfile` backend. Documenter.                                 |
| Lecture streaming interrompue laisse un générateur ouvert          | Faible      | Faible | Utiliser `try/finally` dans le générateur pour fermer le fichier chiffré à coup sûr.      |
| Accès concurrent à `documents_sous_dossiers` depuis GEC et GED     | Faible      | Faible | Contrainte `ON DELETE RESTRICT` suffit. Pas de lock applicatif nécessaire.                |
| `document_principal_id` NULL sur courriers internes brefs           | —           | Faible | Décision confirmée : optionnel. Voir point ouvert dans `docs/schema.md §9`.               |
| Téléchargement DOCX/XLSX déchiffré côté client → fichier en clair sur le poste utilisateur | Élevée | Faible | **Trade-off assumé** : le déchiffrement côté serveur est inévitable pour permettre l'ouverture dans l'application native du client. Documenté dans la politique de sécurité. Mitigation : audit log `document.consulter`, en-tête `Cache-Control: no-store` côté API, sensibilisation utilisateur. Une alternative future serait un viewer Office côté serveur (LibreOffice headless → PDF) pour ne jamais déchiffrer côté client. |

## 12. Jalons

| Jalon                                        | Critère de validation                                          | Cible    |
|----------------------------------------------|----------------------------------------------------------------|----------|
| Migration Alembic 002 OK                     | `alembic upgrade head` sans erreur                             | Sprint 2 |
| `backend/services/crypto.py` testé           | Chiffrement → stockage → déchiffrement → octets identiques     | Sprint 2 |
| Route `POST /api/documents` verte            | CA-01 à CA-09 Pytest                                           | Sprint 2 |
| Route `GET /api/documents/{id}/contenu` verte| CA-04 à CA-06 Pytest                                           | Sprint 2 |
| Visionneuse PDF navigable                    | CA-16 Manuel : PDF s'affiche dans le modal sans erreur console | Sprint 3 |
| Formulaire upload complet                    | CA-16 à CA-20 Manuel : golden path archiviste                  | Sprint 3 |
