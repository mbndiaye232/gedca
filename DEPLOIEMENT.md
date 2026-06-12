# Mise en ligne de Soft GEDCAP

Guide de déploiement cloud : **frontend sur Cloudflare Pages**, **documents sur
Cloudflare R2**, **backend (API + worker + beat + Redis) sur Render**, **base
PostgreSQL sur Render** (déjà créée).

```
Navigateur ──► Cloudflare Pages (React)  ──HTTPS──►  Render : API FastAPI
                                                        │  ├─ Worker Celery
                                                        │  └─ Beat
                                                        ├──►  Render PostgreSQL
                                                        ├──►  Render Redis
                                                        └──►  Cloudflare R2 (documents chiffrés)
```

> **Pourquoi le backend n'est pas sur Cloudflare ?** C'est une appli Python/FastAPI
> avec dépendances natives (OCR Tesseract, libmagic, PyMuPDF, Celery…). Cloudflare
> n'exécute que du JS/WASM. Le backend tourne donc sur Render, à côté de la base.

---

## Prérequis

- [ ] Le code est poussé sur **GitHub** (Render et Cloudflare déploient depuis le repo).
- [ ] La base **PostgreSQL `gedca`** existe sur Render (✅ déjà fait).
- [ ] Un **bucket R2** existe (✅ déjà fait) — il faut juste créer un **token API R2** (ci-dessous).
- [ ] Comptes **Render** et **Cloudflare** actifs.

---

## Étape 1 — Pousser le code

La branche `feat/deploiement-cloud` contient tous les fichiers de déploiement
(`render.yaml`, `frontend/public/_redirects`, le backend R2). Mergez-la sur `main`
(ou déployez directement la branche), puis assurez-vous que GitHub est à jour :

```bash
git push -u origin feat/deploiement-cloud
# … créer la PR, merger sur main …
```

---

## Étape 2 — Cloudflare R2 : créer le token API

Le bucket existe ; il faut des **identifiants S3** pour que le backend y écrive.

1. Cloudflare Dashboard → **R2** → **Manage R2 API Tokens** → **Create API Token**.
2. Permissions : **Object Read & Write**, limité au bucket `softgedcap-documents`.
3. Notez les valeurs affichées (elles ne seront plus jamais montrées) :
   - **Access Key ID** → `R2_ACCESS_KEY_ID`
   - **Secret Access Key** → `R2_SECRET_ACCESS_KEY`
4. **Account ID** : visible dans R2 → Overview (ou dans l'URL du dashboard) → `R2_ACCOUNT_ID`.
5. **Nom du bucket** → `R2_BUCKET` (ex. `softgedcap-documents`).

---

## Étape 3 — Générer les secrets

Deux secrets à générer **une fois** et à conserver précieusement :

```bash
# Clé maître de chiffrement des documents (AES-256, base64) — NE JAMAIS LA PERDRE
python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Secret de signature JWT
openssl rand -hex 32
```

> ⚠️ **`MASTER_KEY` doit être identique sur l'API, le worker et le beat**, et ne
> doit **jamais changer** une fois des documents stockés — sinon ils deviennent
> illisibles. Le blueprint la partage déjà via le groupe `gedcap-partage`.

---

## Étape 4 — Render : déployer le blueprint

1. Render Dashboard → **New +** → **Blueprint**.
2. Connectez le repo GitHub. Render détecte `render.yaml` et propose de créer :
   `gedcap-redis`, `gedcap-api`, `gedcap-worker`, `gedcap-beat`.
3. Avant de valider, renseignez les variables marquées « à fournir » :

| Variable | Valeur | Portée |
|---|---|---|
| `DATABASE_URL` | **Internal Database URL** de la base `gedca` (onglet *Info* de la base) | groupe |
| `MASTER_KEY` | la clé base64 de l'étape 3 | groupe |
| `R2_ACCOUNT_ID` | Account ID Cloudflare | groupe |
| `R2_ACCESS_KEY_ID` | token R2 | groupe |
| `R2_SECRET_ACCESS_KEY` | token R2 | groupe |
| `R2_BUCKET` | `softgedcap-documents` | groupe |
| `ANTHROPIC_API_KEY` | clé Anthropic (sinon laisser vide) | groupe |
| `VOYAGE_API_KEY` | clé Voyage pour l'indexation full-text (sinon vide) | groupe |
| `JWT_SECRET` | le hex de l'étape 3 | API |
| `ALLOWED_ORIGINS` | l'URL Pages (voir étape 6) — **provisoirement** `https://localhost` | API |

> `DATABASE_URL` : collez l'URL Render telle quelle (`postgresql://…`). L'appli la
> convertit automatiquement en `postgresql+asyncpg://`.
>
> `REDIS_URL` est câblée automatiquement sur l'instance `gedcap-redis`.

4. Lancez le déploiement. À chaque démarrage, l'API exécute `alembic upgrade head`
   (les tables se créent toutes seules). Vérifiez l'URL de santé :
   `https://gedcap-api.onrender.com/api/health` → `{"statut":"ok"}`.

> Si Render refuse `type: redis` (offre Key Value récente), créez une instance
> **Key Value** à la main et reliez `REDIS_URL` (Internal URL) dans les 3 services.

---

## Étape 5 — Amorcer la base (premier superviseur)

La base est vide. Créez le premier tenant + compte superviseur via le **Shell** du
service `gedcap-api` (onglet *Shell* sur Render) :

```bash
SEED_TENANT_CODE=monorg \
SEED_ADMIN_LOGIN=admin \
SEED_ADMIN_PASSWORD='UnMotDePasseFort!' \
python -m scripts.seed_dev
```

Le script est idempotent (ne recrée rien si le tenant existe). **Changez le mot de
passe après la première connexion.**

---

## Étape 6 — Cloudflare Pages : déployer le frontend

1. Cloudflare → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Sélectionnez le repo. Réglages de build :
   - **Root directory** : `frontend`
   - **Build command** : `npm run build`
   - **Build output directory** : `dist`
   - **Variable d'environnement** : `VITE_API_URL = https://gedcap-api.onrender.com/api`
     *(l'URL exacte de votre service API Render, suffixée par `/api`)*
3. Déployez. Vous obtenez une URL type `https://soft-gedcap.pages.dev`.

Le fichier `frontend/public/_redirects` est déjà présent : il garantit que les
routes React (`/courriers`, `/reset-mdp`…) fonctionnent au rafraîchissement.

---

## Étape 7 — Boucler le CORS (et les liens email)

Revenez sur le service **`gedcap-api`** (Render) → **Environment** :

- Mettez l'URL Pages **en première position** dans `ALLOWED_ORIGINS` :
  ```
  ALLOWED_ORIGINS=https://soft-gedcap.pages.dev
  ```
  (la 1re origine sert aussi de base aux liens de réinitialisation de mot de passe).
- Sauvegardez → l'API redéploie.

---

## Vérifications finales

- [ ] `GET /api/health` répond `ok`.
- [ ] Connexion sur l'URL Pages avec le compte superviseur.
- [ ] Upload d'un document → il apparaît, **et** un objet `…/<checksum>.enc` apparaît
      dans le bucket R2 (Cloudflare → R2 → bucket → Objects).
- [ ] Ouverture du document dans la visionneuse (déchiffrement OK).
- [ ] Logs du service `gedcap-worker` : tâche d'extraction OCR traitée.
- [ ] (Optionnel) Email de test depuis *Paramètres mail* si SMTP configuré.

---

## Récapitulatif des variables d'environnement

| Variable | API | Worker | Beat | Source |
|---|:--:|:--:|:--:|---|
| `DATABASE_URL` | ✅ | ✅ | ✅ | base Render existante |
| `REDIS_URL` | ✅ | ✅ | ✅ | auto (blueprint) |
| `MASTER_KEY` | ✅ | ✅ | ✅ | généré (étape 3) — identique partout |
| `STORAGE_BACKEND=r2` | ✅ | ✅ | ✅ | fixe |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` | ✅ | ✅ | ✅ | token R2 (étape 2) |
| `JWT_SECRET` | ✅ | — | — | généré (étape 3) |
| `ALLOWED_ORIGINS` | ✅ | — | — | URL Pages (étape 7) |
| `ANTHROPIC_API_KEY` / `VOYAGE_API_KEY` | ✅ | ✅ | — | optionnel (IA full-text) |
| `VITE_API_URL` | — | — | — | Cloudflare Pages (étape 6) |
```
