# PRD-03 — Pipeline d'ingestion

| Champ        | Valeur                                                               |
|--------------|----------------------------------------------------------------------|
| **ID**       | PRD-03                                                               |
| **Module**   | Worker / Pipeline                                                    |
| **Statut**   | Approuvé                                                             |
| **Auteur**   | mbndiaye232                                                          |
| **Date**     | 2026-05-31                                                           |
| **Dépend de**| PRD-01 (Auth), PRD-02 (Stockage chiffré, table `documents`)          |

---

## 1. Contexte & problème

Le guide (§ III) indique que *« le contenu des documents est récupéré et stocké dans la base pour pouvoir faire de la recherche plein texte »* et que *« le contenu des documents PDF, PNG, TIFF, JPG obtenus à l'issue d'opérations de numérisation est récupéré à l'aide d'un logiciel OCR »*. Trois voies d'entrée sont décrites : unitaire (navigateur), lot depuis un dossier, et récupération depuis les emails.

PRD-02 a posé la couche de stockage synchrone : le fichier est chiffré et créé en base, mais sans texte OCR ni embedding. Ce PRD ajoute le worker Celery qui enrichit chaque document après son dépôt — quelle que soit sa voie d'entrée — et active les deux entrées supplémentaires (dossier surveillé et polling IMAP).

## 2. Objectifs

- OBJ-1 : Infrastructure Celery + Redis opérationnelle ; toute tâche longue (OCR, embedding, IMAP) exécutée hors de la boucle FastAPI.
- OBJ-2 : Chaîne d'enrichissement unifiée : tout fichier entrant, par n'importe quelle voie, passe par la même séquence OCR → FTS → embedding.
- OBJ-3 : OCR via Tesseract `fra` + `ocrmypdf` : texte extracté en clair dans `texte_ocr`, PDF/A cherchable produit pour les scans.
- OBJ-4 : Génération d'embeddings 1024 dimensions interchangeable selon `AI_PROVIDER` : Voyage AI (cloud SaaS) ou `intfloat/multilingual-e5-large` via Ollama (on-prem).
- OBJ-5 : Watcher de dossier surveillé (watchdog) pour l'ingestion automatique de fichiers déposés côté serveur.
- OBJ-6 : Polling IMAP périodique (Celery Beat) + écran d'intégration des pièces jointes d'email (écran 2.3).
- OBJ-7 : Upload par lot depuis le navigateur avec barre de progression (écran 2.2).
- OBJ-8 : File de quarantaine + notification archiviste en cas d'échec irrémédiable.

## 3. Non-objectifs (hors périmètre)

- Suggestions de classification IA (catégorie, mots-clés proposés) → PRD-07.
- Recherche FTS + sémantique dans l'UI → PRD-04 (les champs sont alimentés ici, l'interface de recherche est ailleurs).
- Envoi d'alertes retard par email → PRD-06 (même infrastructure Celery Beat, tâche différente).
- Sauvegarde base / documents via Celery → PRD-08.
- Scan depuis un périphérique physique connecté au poste (§ X du guide) — hors scope web.

## 4. Utilisateurs cibles

| Rôle             | Ce qu'ils font dans ce module                                               |
|------------------|-----------------------------------------------------------------------------|
| `superviseur`    | Configure les paramètres IMAP, consulte les documents en quarantaine, relance les traitements en erreur. |
| `archiviste`     | Lance les uploads par lot, intègre des pièces jointes depuis l'interface IMAP, complète les métadonnées après ingestion. |
| `agent_standard` | Aucune action directe — bénéficie des résultats (OCR, search) sans interagir avec le pipeline. |

## 5. Fonctionnalités

### 5.1 Infrastructure Celery + Redis

**Description :** Un worker Celery distinct du processus FastAPI consomme les tâches déposées dans un broker Redis.

**Règles métier :**
- RG-1 : Un seul broker Redis partagé entre l'API FastAPI et le worker Celery. URL via `REDIS_URL`.
- RG-2 : Deux queues Celery distinctes :
  - `ingestion` — tâches OCR/embedding, haute priorité, peut être longue.
  - `notifications` — envois email, basse priorité, courte durée.
- RG-3 : Concurrence worker configurable via `CELERY_WORKER_CONCURRENCY` (défaut : 2). Sur on-prem avec Ollama, garder à 1 pour éviter la saturation GPU/CPU.
- RG-4 : Celery Beat (planificateur) tourne dans un processus séparé et gère les tâches périodiques (polling IMAP, alerte retard).
- RG-5 : Toutes les tâches Celery sont idempotentes : relancer une tâche sur un document déjà traité ne produit pas de doublon.
- RG-6 : En cas d'échec, la tâche est retentée 3 fois avec backoff exponentiel (30 s, 2 min, 10 min) avant d'être envoyée en quarantaine.

---

### 5.2 Chaîne de traitement unifiée (pipeline)

**Description :** Quelle que soit la voie d'entrée (upload, watcher, IMAP), le même pipeline Celery est déclenché. Point d'entrée unique : `ingerer_document(document_id, tenant_id)`.

**Séquence des tâches (Celery canvas `chain`) :**

```
ingerer_document(document_id, tenant_id)
  │
  ├─ 1. tache_ocr          → remplit texte_ocr, génère le PDF/A (si applicable)
  │                           met à jour statut = 'en_cours'
  │
  ├─ 2. tache_fts_update   → déclenché automatiquement par le trigger PostgreSQL
  │                           (BEFORE INSERT/UPDATE sur titre, mots_cles, resume, texte_ocr)
  │                           Pas de tâche Celery dédiée — c'est le trigger SQL.
  │
  ├─ 3. tache_embedding    → calcule le vecteur 1024d, stocke dans documents.embedding
  │
  └─ 4. tache_finaliser    → statut = 'pret', updated_at = NOW(), inscrit audit_log
```

**Règles métier :**
- RG-1 : Le document est créé par PRD-02 avec `statut='en_cours'` dès que la tâche est dispatchée. Il est visible pour la visionneuse, mais pas encore cherchable par contenu OCR.
- RG-2 : Chaque étape de la chaîne écrit ses résultats directement dans `documents` avant de passer à l'étape suivante. Si le worker redémarre, la tâche reprend à la première étape incomplète (idempotence via lecture du statut).
- RG-3 : Si `texte_ocr` est déjà non-NULL (re-traitement d'un document), l'OCR est quand même relancé et écrase la valeur précédente.
- RG-4 : Un échec à n'importe quelle étape après 3 tentatives → `tache_quarantaine`.

---

### 5.3 OCR — Tesseract + ocrmypdf

**Description :** Extraction du texte des fichiers scannés ou des images. Génération d'un PDF/A cherchable pour les PDFs non-textuels.

**Règles métier :**
- RG-1 : Avant l'OCR, le fichier chiffré est déchiffré dans un répertoire temporaire dédié au worker (`WORKER_TEMP_DIR`). Le fichier temporaire est supprimé après la tâche, succès ou échec.
- RG-2 : Selon le type MIME du document :
  - **PDF** : `ocrmypdf --language fra --skip-text` — si le PDF contient déjà du texte, le texte est extrait directement (pdfminer.six) ; s'il est scanné, OCR est appliqué et un PDF/A cherchable est produit.
  - **Images** (JPEG, PNG, TIFF, WEBP) : `ocrmypdf --language fra` convertit l'image en PDF/A avec texte incrusté. Le nouveau PDF/A **remplace** le fichier chiffré stocké (nouveau chiffrement, nouvelle entrée `document_versions`).
  - **DOCX / ODT** : extraction de texte via `python-docx` / `odfpy`. Pas d'OCR. Pas de conversion PDF/A en v1.
  - **XLSX / ODS** : extraction via `openpyxl` / `odfpy`. Texte des cellules concaténé.
  - **Autres** : `texte_ocr = NULL`, `statut='pret'` (le document reste accessible, juste non cherchable par contenu).
- RG-3 : Le texte extrait est tronqué à 10 Mo avant stockage dans `texte_ocr` pour éviter les enregistrements PostgreSQL excessivement lourds.
- RG-4 : La langue Tesseract utilisée est `fra` (français). Configurable par tenant via `tenants.ai_config.ocr_lang` si besoin futur.
- RG-5 : Si ocrmypdf échoue (fichier corrompu, format non supporté) : `texte_ocr = NULL`, pipeline continue vers `tache_embedding` avec le titre + mots-clés comme source de texte pour l'embedding.

---

### 5.4 Génération d'embeddings — abstraction `AI_PROVIDER`

**Description :** Le service `backend/services/ai.py` expose une interface unique, avec deux implémentations interchangeables selon `tenants.ai_provider`.

**Interface :**
```python
class AIProvider(ABC):
    async def generate_embedding(self, text: str) -> list[float]: ...
```

**Implémentation `anthropic` (SaaS) :**
- API Voyage AI, modèle `voyage-3`, dimension 1024.
- Clé API via `VOYAGE_API_KEY`.
- Texte d'entrée : `titre + " " + mots_cles + " " + resume + " " + texte_ocr[:4096]`.
- Tronquer à 32 000 tokens (limite voyage-3).

**Implémentation `ollama` (on-prem) :**
- Modèle `intfloat/multilingual-e5-large` via Ollama REST API (`/api/embeddings`).
- URL via `OLLAMA_URL` (ex : `http://ollama:11434`).
- Même dimension 1024.
- Format d'entrée requis : *passage:* prefix pour le texte de document, *query:* pour les requêtes de recherche.

**Règles métier :**
- RG-1 : Le provider est lu depuis `tenants.ai_provider` du tenant courant — un tenant peut utiliser Ollama pendant qu'un autre utilise Anthropic sur la même instance SaaS.
- RG-2 : Si le texte d'entrée est vide (pas de texte OCR, pas de métadonnées) → `embedding = NULL`. La recherche sémantique sur ce document retourne 0 résultat sans erreur.
- RG-3 : L'embedding est **une suggestion technique**, pas une donnée métier : il n'est jamais affiché à l'utilisateur. La règle « IA suggère, humain valide » s'applique aux métadonnées (PRD-07), pas aux embeddings qui sont transparents.
- RG-4 : Si l'API IA est indisponible (timeout, quota) : l'embedding est laissé à `NULL`, `statut='pret'` quand même. L'archiviste est notifié par bandeau (pas par email). Une tâche de réessai est planifiée dans 1 h.

---

### 5.5 Modification du comportement d'upload (rétrofit PRD-02)

**Description :** Le `POST /api/documents` (PRD-02) est modifié pour dispatcher une tâche Celery après avoir stocké le fichier.

**Règles métier :**
- RG-1 : Le `statut` à la création passe de `'pret'` (PRD-02) à `'en_cours'` dès qu'une tâche est dispatchée.
- RG-2 : La réponse HTTP 201 est retournée **avant** la fin du pipeline — l'upload reste synchrone, l'enrichissement est asynchrone.
- RG-3 : La tâche est dispatchée dans la queue `ingestion` avec `countdown=0` (immédiatement).
- RG-4 : Le document est consultable (visionneuse) même en `statut='en_cours'`. La recherche plein texte par contenu ne fonctionnera qu'après passage à `'pret'`.
- RG-5 : L'UI affiche un indicateur visuel (spinner / badge « En traitement ») sur les documents `statut='en_cours'`.

---

### 5.6 Upload par lot depuis le navigateur (écran 2.2 — 🟠 P1)

**Description :** L'archiviste sélectionne un dossier local depuis son navigateur. Les fichiers sont uploadés un par un avec une catégorie et un emplacement physique communs.

**Règles métier :**
- RG-1 : Contrainte métier du guide : **tous les fichiers d'un lot partagent la même catégorie** et le même sous-dossier physique (optionnel). Ces deux valeurs sont choisies avant de lancer l'envoi.
- RG-2 : Le frontend itère sur les fichiers via `<input type="file" webkitdirectory>` et les envoie séquentiellement au `POST /api/documents`. Pas de multipart multi-fichiers — un appel par fichier.
- RG-3 : Une barre de progression affiche l'avancement global (N fichiers envoyés / total) et le statut par fichier (en cours, succès, doublon, erreur).
- RG-4 : Un doublon (HTTP 409) est signalé visuellement mais n'interrompt pas le lot.
- RG-5 : À la fin du lot, un lien vers la liste filtrée des documents créés à cette session permet à l'archiviste de compléter ou corriger les métadonnées.
- RG-6 : Pas de transaction globale sur le lot : chaque fichier est traité indépendamment.

---

### 5.7 Watcher de dossier surveillé

**Description :** Un service `watchdog` Python, lancé au démarrage du worker, observe un répertoire serveur et ingère automatiquement tout nouveau fichier.

**Règles métier :**
- RG-1 : Le répertoire surveillé est configuré par `WATCHER_ROOT` (variable d'env). En on-prem, c'est un volume local. En SaaS, c'est un volume NFS partagé ou monté via S3FS.
- RG-2 : Dès qu'un fichier `CREATE` est détecté (événement `watchdog.events.FileCreatedEvent`) :
  1. Attendre 2 s (fichier potentiellement en cours d'écriture).
  2. Vérifier que la taille du fichier n'a pas changé entre deux lectures (fichier complètement écrit).
  3. Dispatcher `ingerer_document` via Celery.
- RG-3 : Le tenant est déterminé par la structure du répertoire : `WATCHER_ROOT/{tenant_id}/`. Si le sous-dossier ne correspond à aucun tenant actif, le fichier est ignoré et loggué.
- RG-4 : L'enregistrement `documents` est créé avec `origine='watcher'`, titre = nom de fichier sans extension, `categorie_id = NULL` → `statut='pret'` après pipeline mais avec `metadata.a_completer = true`.
- RG-5 : L'archiviste du tenant reçoit une notification email (tâche `notifications`) listant les documents déposés par le watcher depuis la veille (digest quotidien, pas un email par fichier).
- RG-6 : Le watcher ne supprime pas les fichiers source du répertoire surveillé. C'est à l'archiviste de les retirer après vérification.
- RG-7 : Le watcher ne tourne que si `WATCHER_ENABLED=true` (désactivé par défaut en SaaS multi-tenant — chaque tenant aurait un volume dédié, ce qui est gérable mais à activer explicitement).

---

### 5.8 Polling IMAP (écrans 2.3 + 4.7 — 🟠 P1)

**Description :** Un job Celery Beat scrute périodiquement la boîte IMAP configurée par tenant et propose à l'archiviste d'intégrer les pièces jointes trouvées.

**Configuration IMAP (ajout sur `tenants`) :**
Les colonnes suivantes sont ajoutées dans la migration 003 :

| Colonne              | Type        | Description                                      |
|----------------------|-------------|--------------------------------------------------|
| `imap_host`          | VARCHAR(255)| Serveur IMAP (ex : `imap.gmail.com`)             |
| `imap_port`          | INTEGER     | Défaut 993                                       |
| `imap_user`          | VARCHAR(255)| Identifiant de connexion                         |
| `imap_password_enc`  | BYTEA       | Mot de passe chiffré avec la clé maître          |
| `imap_folder`        | VARCHAR(255)| Dossier à scruter (défaut : `INBOX`)             |
| `imap_actif`         | BOOLEAN     | Active/désactive le polling pour ce tenant       |
| `imap_dernier_uid`   | BIGINT      | UID du dernier message traité (curseur de reprise)|

**Tâche périodique (`poller_imap_tous_tenants`) :**
- RG-1 : Exécutée par Celery Beat toutes les 15 minutes (configurable via `IMAP_POLL_INTERVAL_MIN`).
- RG-2 : Pour chaque tenant avec `imap_actif = TRUE`, dispatcher `poller_imap(tenant_id)`.
- RG-3 : `poller_imap(tenant_id)` se connecte en IMAP TLS, sélectionne le folder, récupère les messages dont l'UID > `imap_dernier_uid`.
- RG-4 : Pour chaque message, les pièces jointes sont extraites, chiffrées avec la clé tenant et écrites sous `{STORAGE_ROOT}/imap-staging/{tenant_id}/{uuid}.enc`. Une entrée est créée dans `imap_pieces_jointes` (métadonnées uniquement, pas de blob — voir §9). Elles ne sont **pas** ingérées automatiquement dans la GED — l'archiviste les intègre manuellement depuis l'écran 2.3.
- RG-5 : `imap_dernier_uid` est mis à jour après chaque polling réussi.
- RG-6 : Si la connexion IMAP échoue 3 fois consécutives → notification superviseur + `imap_actif` mis à `FALSE` automatiquement (évite les reconnexions répétées sur un compte bloqué).

**Écran 2.3 — Interface IMAP (`/documents/imap`) :**
- RG-7 : Filtres : date de réception (intervalle), mots-clés dans l'objet ou le corps.
- RG-8 : Le tableau du haut liste les messages trouvés (expéditeur, objet, date, nombre de pièces jointes). Cliquer sur un message filtre le tableau du bas.
- RG-9 : Le tableau du bas liste les pièces jointes (nom, type MIME, taille).
- RG-10 : Bouton « Intégrer dans la GED » → mini-formulaire pré-rempli (titre = nom de la pièce jointe, champs métadonnées à compléter). Valider déclenche le pipeline complet.
- RG-11 : Guide (§ III.3) : *« il n'y a pas de numéro de sous-dossier pour les documents récupérés à partir des mails »* — le champ emplacement physique est masqué dans ce formulaire (disponible en modification ultérieure).
- RG-12 : Un message intégré est marqué comme traité dans `imap_pieces_jointes` (`integre=TRUE`, `integre_at`, `integre_par`, `document_id`) et n'apparaît plus dans la liste. Le fichier staging chiffré est conservé jusqu'à la purge quotidienne (TTL `IMAP_STAGING_TTL_DAYS`).

---

### 5.9 Quarantaine et notification d'échec

**Description :** Quand la pipeline échoue définitivement (3 tentatives épuisées), le document est mis en quarantaine et l'archiviste est notifié.

**Règles métier :**
- RG-1 : `tache_quarantaine(document_id, raison)` :
  1. Met `documents.statut = 'quarantaine'`.
  2. Stocke la raison dans `documents.metadata.quarantaine_raison`.
  3. Stocke le traceback dans `documents.metadata.quarantaine_traceback` (tronqué à 2000 caractères).
  4. Dispatche `tache_notification_echec` vers la queue `notifications`.
- RG-2 : Un document en quarantaine est invisible dans les recherches mais reste consultable par un archiviste ou superviseur via un filtre explicite `statut=quarantaine`.
- RG-3 : L'archiviste peut déclencher une re-tentative manuelle depuis la fiche du document (bouton « Relancer le traitement ») → `POST /api/documents/{id}/relancer`.
- RG-4 : Une re-tentative remet `statut='en_cours'` et dispatche la chaîne depuis le début.
- RG-5 : `tache_notification_echec` envoie un email à l'archiviste qui a déposé le document (`documents.created_by`) via les paramètres SMTP du tenant. Objet : *« [GEDCA] Échec de traitement — {titre} »*.
- RG-6 : Si l'envoi email échoue (SMTP non configuré, erreur réseau), l'échec est loggué mais ne provoque pas d'autre quarantaine.
- RG-7 : L'action `document.quarantaine` est inscrite dans `audit_log` avec la raison en payload.

---

### 5.10 Monitoring et statuts de traitement

**Description :** L'interface expose l'état du pipeline pour permettre à l'archiviste de suivre ses dépôts.

**Règles métier :**
- RG-1 : `GET /api/documents?statut=en_cours` retourne les documents encore en traitement du tenant courant.
- RG-2 : `GET /api/documents?statut=quarantaine` retourne les documents en quarantaine (archiviste et superviseur uniquement).
- RG-3 : Sur chaque fiche de document, un badge indique le statut (`En traitement`, `Prêt`, `Erreur`, `Quarantaine`) avec une icône colorée.
- RG-4 : Endpoint de santé worker : `GET /api/admin/worker/ping` (superviseur) — vérifie que le worker Celery répond sur Redis. Utilisé par docker-compose healthcheck.

---

## 6. Critères d'acceptation

| ID    | Critère                                                                                                                           | Type   |
|-------|-----------------------------------------------------------------------------------------------------------------------------------|--------|
| CA-01 | Upload d'un PDF scanné (sans texte) → après pipeline, `texte_ocr` non-NULL, `recherche_fts` alimenté.                            | Pytest |
| CA-02 | Upload d'un PDF avec texte existant → `texte_ocr` extrait sans relancer OCR (skip-text ocrmypdf).                                | Pytest |
| CA-03 | Upload d'un JPEG → converti en PDF/A, texte OCR extrait, `documents.mime` mis à jour à `application/pdf`.                        | Pytest |
| CA-04 | Upload d'un DOCX → `texte_ocr` extrait via python-docx sans OCR.                                                                 | Pytest |
| CA-05 | Type MIME non supporté pour OCR → `texte_ocr = NULL`, `statut='pret'` quand même (pas de quarantaine).                           | Pytest |
| CA-06 | Provider `anthropic` : `generate_embedding` retourne une liste de 1024 floats.                                                    | Pytest |
| CA-07 | Provider `ollama` : `generate_embedding` retourne une liste de 1024 floats.                                                       | Pytest |
| CA-08 | `generate_embedding` appelé avec texte vide → `embedding = NULL`, pas d'exception.                                               | Pytest |
| CA-09 | Isolation tenant : le pipeline d'un tenant A ne peut pas accéder aux fichiers chiffrés du tenant B.                               | Pytest |
| CA-10 | Tâche qui échoue 3 fois → `statut='quarantaine'`, raison dans `metadata.quarantaine_raison`.                                      | Pytest |
| CA-11 | `POST /api/documents/{id}/relancer` → `statut` repasse à `'en_cours'`, tâche redispatchée.                                        | Pytest |
| CA-12 | Tâche idempotente : relancer une tâche sur un document déjà `'pret'` ne crée pas de doublon en `document_versions`.               | Pytest |
| CA-13 | Watcher : dépôt d'un fichier dans `WATCHER_ROOT/{tenant_id}/` → document créé en base avec `origine='watcher'`.                  | Pytest |
| CA-14 | IMAP poller : simulation d'un serveur IMAP avec pièce jointe → entrée créée dans `imap_pieces_jointes`.                           | Pytest |
| CA-15 | IMAP : 3 échecs consécutifs de connexion → `imap_actif = FALSE` sur le tenant, notification superviseur.                         | Pytest |
| CA-16 | Fichier temporaire déchiffré supprimé du `WORKER_TEMP_DIR` après la tâche, même en cas d'exception.                               | Pytest |
| CA-17 | UI — Upload lot : barre de progression avance à chaque fichier envoyé. Un doublon n'interrompt pas le lot.                        | Manuel |
| CA-18 | UI — Statut `'en_cours'` visible (badge spinner) sur le document dans la liste après upload.                                      | Manuel |
| CA-19 | UI — Tableau IMAP : sélectionner un message filtre les pièces jointes. Bouton « Intégrer » ouvre le formulaire pré-rempli.        | Manuel |
| CA-20 | UI — Document en quarantaine : bouton « Relancer » visible pour l'archiviste, `statut` repasse à `'En traitement'` après clic.   | Manuel |

## 7. Contraintes techniques

- **OCR** : packages système `tesseract-ocr tesseract-ocr-fra ocrmypdf` dans l'image Docker worker.
- **Extraction texte** : `pdfminer.six` (PDF), `python-docx` (DOCX), `openpyxl` (XLSX), `odfpy` (ODT/ODS).
- **Embeddings** : `voyageai` SDK (anthropic) ou appels HTTP directs Ollama REST API (pas de dépendance `ollama` Python — trop couplé).
- **Broker** : Redis 7+. Pas de RabbitMQ en v1 (complexité inutile).
- **Celery** : `celery[redis]` version 5.x. Serializer : `json` (pas pickle — sécurité).
- **Fichiers temporaires** : stockés dans `WORKER_TEMP_DIR` (volume dédié au worker, pas `/tmp` système). Nettoyage via `try/finally` dans chaque tâche.
- **Watcher** : `watchdog` 3.x. Ne pas utiliser le mode polling sur Linux (utiliser inotify).
- **IMAP** : `imapclient` (plus fiable que `imaplib` brut pour la gestion des UID).
- **Async/sync** : les tâches Celery sont synchrones (`def`, pas `async def`). Les appels API IA utilisent le SDK synchrone ou `requests`.
- **Taille max texte OCR** : 10 Mo. Au-delà, tronquer avec marqueur `[TRONQUÉ]` en fin de texte.
- **Timeout tâche OCR** : 10 minutes (`soft_time_limit=540, time_limit=600`).
- **Audit** : `document.ocr_complet`, `document.embedding_calcule`, `document.quarantaine` dans `audit_log`.

## 8. API endpoints

| Méthode | Route                                    | Rôles autorisés          | Description                                                     |
|---------|------------------------------------------|--------------------------|-----------------------------------------------------------------|
| POST    | `/api/documents/{id}/relancer`           | archiviste, superviseur  | Relancer la pipeline sur un document en erreur/quarantaine      |
| GET     | `/api/documents?statut=en_cours`         | archiviste, superviseur  | Lister les documents en traitement (filtre sur statut)          |
| GET     | `/api/documents?statut=quarantaine`      | archiviste, superviseur  | Lister les documents en quarantaine                             |
| GET     | `/api/imap/messages`                     | archiviste, superviseur  | Lister les messages IMAP filtrés (date, mots-clés)              |
| GET     | `/api/imap/messages/{uid}/pieces`        | archiviste, superviseur  | Pièces jointes d'un message                                     |
| POST    | `/api/imap/pieces/{imap_piece_id}/integrer` | archiviste, superviseur | Intégrer une pièce jointe dans la GED (déclenche la pipeline) |
| GET     | `/api/admin/worker/ping`                 | superviseur              | Healthcheck worker Celery                                       |
| PUT     | `/api/structure` (retrofit PRD-01)       | superviseur              | Ajoute les champs IMAP (`imap_host`, `imap_port`, etc.)         |

## 9. Modèle de données impacté

**Migration Alembic 003** :

**Modification de `tenants`** — ajout des colonnes IMAP :
```sql
ALTER TABLE tenants ADD COLUMN imap_host         VARCHAR(255);
ALTER TABLE tenants ADD COLUMN imap_port         INTEGER DEFAULT 993;
ALTER TABLE tenants ADD COLUMN imap_user         VARCHAR(255);
ALTER TABLE tenants ADD COLUMN imap_password_enc BYTEA;
ALTER TABLE tenants ADD COLUMN imap_folder       VARCHAR(255) DEFAULT 'INBOX';
ALTER TABLE tenants ADD COLUMN imap_actif        BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE tenants ADD COLUMN imap_dernier_uid  BIGINT;
```

**Nouvelle table `imap_pieces_jointes`** — métadonnées des pièces jointes en attente d'intégration (le contenu binaire est stocké sur disque chiffré, **pas en base**, conformément à PRD-02 §7) :

```sql
CREATE TABLE imap_pieces_jointes (
  id                BIGSERIAL PRIMARY KEY,
  tenant_id         BIGINT NOT NULL REFERENCES tenants(id),
  message_uid       BIGINT NOT NULL,
  message_sujet     TEXT,
  message_from      VARCHAR(255),
  message_date      TIMESTAMPTZ,
  nom_fichier       VARCHAR(512) NOT NULL,
  mime              VARCHAR(128),
  taille_octets     BIGINT,
  -- Référence vers le fichier chiffré sur disque (pas de blob en base)
  chemin_stockage   TEXT NOT NULL,                    -- {STORAGE_ROOT}/imap-staging/{tenant_id}/{uuid}.enc
  nonce             BYTEA NOT NULL,                   -- nonce AES-GCM 12 octets
  checksum_sha256   CHAR(64) NOT NULL,
  integre           BOOLEAN NOT NULL DEFAULT FALSE,
  integre_at        TIMESTAMPTZ,
  integre_par       BIGINT REFERENCES agents(id),
  document_id       BIGINT REFERENCES documents(id),  -- rempli après intégration
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, message_uid, nom_fichier)
);

CREATE INDEX idx_imap_tenant_integre ON imap_pieces_jointes (tenant_id, integre);
```

> La pièce jointe brute est chiffrée par le poller IMAP avec la même clé tenant que les documents (HKDF), stockée sous `{STORAGE_ROOT}/imap-staging/{tenant_id}/{uuid}.enc`. Lors de l'intégration : déchiffrement → recalcul du checksum (déduplication possible avec un `documents` existant) → re-chiffrement final sous le chemin standard `{STORAGE_ROOT}/{tenant_id}/{checksum}.enc` → suppression du staging.
>
> Une tâche Celery Beat quotidienne purge les fichiers de `imap-staging` correspondant à des entrées `integre=TRUE` ou plus anciennes que `IMAP_STAGING_TTL_DAYS` (défaut 30 jours).

## 10. Dépendances inter-modules

- Requiert : PRD-02 (table `documents`, service crypto, `STORAGE_ROOT`).
- Requiert : PRD-01 (JWT pour authentifier les endpoints, `tenant_id`).
- Requis par :
  - PRD-04 (GED — la recherche FTS et sémantique utilise `texte_ocr`, `recherche_fts`, `embedding` alimentés ici).
  - PRD-06 (GEC — le job d'alerte retard email réutilise l'infrastructure Celery Beat posée ici).
  - PRD-07 (IA avancée — les suggestions de classification s'insèrent dans la chaîne `ingerer_document`).

## 11. Risques & points ouverts

| Risque / Question ouverte                                                   | Probabilité | Impact  | Mitigation / décision                                                                               |
|-----------------------------------------------------------------------------|-------------|---------|-----------------------------------------------------------------------------------------------------|
| OCR très lent sur gros PDF (> 100 pages) → timeout worker                  | Moyenne     | Moyen   | `soft_time_limit=540s`. Découper les PDFs longs en batches de pages si nécessaire (à confirmer en tests de charge). |
| Passage de l'image JPEG au PDF/A change le `mime` et le fichier stocké → coordination avec PRD-02 | Faible | Moyen | Le remplacement du fichier passe par la mécanique de versionnement de PRD-02 (RG-2 de §5.3). |
| `WORKER_TEMP_DIR` sature si des tâches restent bloquées                     | Faible      | Moyen   | Tâche de nettoyage quotidienne Celery Beat : purger les fichiers temporaires de plus de 24 h.       |
| Quota API Voyage AI dépassé → embeddings à NULL pour plusieurs documents    | Moyenne     | Faible  | Retry avec backoff. Bandeau superviseur. La recherche FTS reste fonctionnelle même sans embedding.  |
| Le dossier `imap-staging` peut grossir si peu d'archivistes actifs          | Moyenne     | Faible  | Tâche Celery Beat quotidienne : purger les fichiers staging de plus de `IMAP_STAGING_TTL_DAYS` jours (défaut 30, configurable). |
| Watcher sur volume NFS en SaaS : latence événements `inotify`               | Faible      | Faible  | Fallback sur `watchdog` polling mode si `inotify` non disponible (`WATCHER_FORCE_POLLING=true`).   |
| Celery Beat singleton : deux instances du beat en parallèle → doublons       | Faible      | Moyen   | Un seul conteneur Beat dans `docker-compose`. Documenter dans le guide de déploiement.             |

## 12. Jalons

| Jalon                                             | Critère de validation                                              | Cible    |
|---------------------------------------------------|--------------------------------------------------------------------|----------|
| Celery + Redis opérationnel                       | `worker ping` OK, tâche simple consommée depuis l'API              | Sprint 3 |
| Pipeline OCR complet                              | CA-01 à CA-05 Pytest verts                                         | Sprint 3 |
| Embeddings (anthropic + ollama)                   | CA-06 à CA-08 Pytest, dimension 1024 vérifiée                      | Sprint 3 |
| Upload navigateur → pipeline async                | CA-09, badge `en_cours` visible UI (CA-18 Manuel)                  | Sprint 4 |
| Quarantaine + relance                             | CA-10, CA-11 Pytest ; CA-20 Manuel                                 | Sprint 4 |
| Watcher fonctionnel                               | CA-13 Pytest                                                       | Sprint 4 |
| IMAP poller + écran 2.3                           | CA-14, CA-15 Pytest ; CA-19 Manuel                                 | Sprint 5 |
| Upload par lot (écran 2.2)                        | CA-17 Manuel : lot de 10 fichiers sans interruption                | Sprint 5 |
