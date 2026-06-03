# PRD-01 — Socle Auth & RBAC

| Champ        | Valeur                                                          |
|--------------|-----------------------------------------------------------------|
| **ID**       | PRD-01                                                          |
| **Module**   | Socle                                                           |
| **Statut**   | Approuvé                                                        |
| **Auteur**   | mbndiaye232                                                     |
| **Date**     | 2026-05-31                                                      |
| **Dépend de**| PRD-00 (Vision & Architecture)                                  |

---

## 1. Contexte & problème

Le guide (§ Introduction & § VI. Agents) décrit un système où au lancement le formulaire d'authentification identifie l'agent et adapte les menus selon son statut (administrateur ou non). Dans l'app desktop, le « superviseur » a accès à tout ; les autres agents voient des menus restreints. GEDCA doit reproduire ce modèle avec trois rôles formels et une isolation complète entre tenants.

C'est le premier module à livrer : toutes les autres fonctionnalités en dépendent.

## 2. Objectifs

- OBJ-1 : Authentification sécurisée (bcrypt + JWT) permettant à un agent de se connecter avec son login/mot de passe.
- OBJ-2 : Contrôle d'accès basé sur les rôles (`superviseur`, `archiviste`, `agent_standard`) appliqué sur chaque route FastAPI.
- OBJ-3 : Gestion complète des agents par le superviseur (créer, modifier, désactiver — jamais supprimer si courriers liés).
- OBJ-4 : Gestion des départements et de la structure de l'organisation.
- OBJ-5 : Audit log systématique sur toutes les actions sensibles.
- OBJ-6 : Isolation multi-tenant : `tenant_id` injecté automatiquement, jamais accepté en paramètre client.

## 3. Non-objectifs (hors périmètre)

- Authentification LDAP/AD (prévu v2 — `AUTH_PROVIDER=local|ldap` architecturalement réservé).
- Récupération de mot de passe par email (peut attendre une itération ultérieure).
- SSO / OAuth2.
- Gestion fine des permissions par ressource (un ACL document-à-document — le guide ne le fait pas).

## 4. Utilisateurs cibles

| Rôle             | Ce qu'ils font dans ce module                                              |
|------------------|----------------------------------------------------------------------------|
| `superviseur`    | Crée et gère tous les comptes agents, les départements, la structure. Voit les logs d'audit. |
| `archiviste`     | Se connecte, consulte son profil, modifie son mot de passe.                |
| `agent_standard` | Se connecte, consulte son profil, modifie son mot de passe.                |

## 5. Fonctionnalités

### 5.1 Authentification (écran 0.1 — 🔴 P0)

**Description :** Un agent saisit son login et son mot de passe. Le système vérifie les credentials, retourne un JWT et redirige vers `/accueil`.

**Règles métier :**
- RG-1 : Le message d'erreur ne révèle pas si le login existe (`« Identifiants invalides »` dans les deux cas).
- RG-2 : Un agent avec `actif = FALSE` ne peut pas se connecter.
- RG-3 : La réponse JWT contient `agent_id`, `tenant_id`, `role`, `nom`, `prenom`. Jamais le `password_hash`.
- RG-4 : Le JWT a une durée de vie configurable (`JWT_EXPIRE_MINUTES`, défaut 480 min = 8 h).
- RG-5 : Chaque connexion réussie met à jour `agents.derniere_connexion` et écrit dans `audit_log` (action `login`).
- RG-6 : Chaque échec d'authentification écrit dans `audit_log` (action `login_echec`) avec l'IP.

**Comportement attendu :**
1. L'agent saisit login + mot de passe et soumet.
2. `POST /api/auth/login` retourne `{ access_token, token_type, agent }` avec HTTP 200, ou HTTP 401.
3. Le frontend stocke le token (mémoire ou `localStorage` selon la politique choisie) et redirige.
4. Toutes les routes protégées refusent avec HTTP 401 si le token est absent ou expiré.

**Champs / données concernés :** `agents.login`, `agents.password_hash`, `agents.actif`, `agents.derniere_connexion`, `audit_log`.

---

### 5.2 Déconnexion

**Description :** L'agent clique sur « Déconnexion » dans le header/sidebar.

**Règles métier :**
- RG-1 : Le frontend supprime le token. En v1, pas de liste noire côté serveur (stateless JWT).
- RG-2 : Redirige vers `/login`.

---

### 5.3 Dépendance FastAPI `get_current_agent` (technique)

**Description :** Toutes les routes protégées injectent l'agent courant via une dépendance FastAPI qui décode le JWT, charge l'agent en base, vérifie `actif = TRUE` et expose `tenant_id`.

**Règles métier :**
- RG-1 : Aucun endpoint métier n'accepte `tenant_id` comme paramètre client — toujours extrait du JWT.
- RG-2 : La dépendance expose une variante par rôle (`require_superviseur`, `require_archiviste_ou_plus`) pour les vérifications RBAC inline.

---

### 5.4 Gestion des agents (écrans 4.3, 4.4 — 🔴 P0)

**Description :** Le superviseur peut lister, créer, modifier et désactiver des agents.

**Règles métier :**
- RG-1 : Le login doit être unique par tenant (contrainte `UNIQUE (tenant_id, login)` en base).
- RG-2 : L'email doit être unique par tenant s'il est fourni.
- RG-3 : Un agent ayant des courriers liés **ne peut pas être supprimé** (physiquement) — seulement désactivé (`actif = FALSE`). Le guide (§ VI.2) le précise explicitement.
- RG-4 : Seul le superviseur peut créer / modifier / désactiver d'autres agents.
- RG-5 : Un agent peut modifier son propre email, téléphone, photo et mot de passe (écran 0.4).
- RG-6 : Le mot de passe est haché avec bcrypt avant stockage, jamais loggué.
- RG-7 : La création d'un agent écrit dans `audit_log` (action `agent.create`).
- RG-8 : La désactivation écrit dans `audit_log` (action `agent.desactiver`).

**Champs :** `agents.login`, `password_hash`, `nom`, `prenom`, `email`, `telephone`, `photo_chemin`, `fonction`, `departement_id`, `role_id`, `actif`.

---

### 5.5 Gestion des départements (écran 4.5 — 🔴 P0)

**Description :** Le superviseur crée et modifie les départements (services) auxquels les agents sont affectés.

**Règles métier :**
- RG-1 : Libellé unique par tenant.
- RG-2 : Un département avec des agents actifs ne peut pas être supprimé (retourner HTTP 409 avec message explicite).
- RG-3 : Soft delete possible (`actif = FALSE`) si le département n'a plus d'agents actifs.

**Champs :** `departements.libelle`, `actif`.

---

### 5.6 Structure de l'organisation (écran 4.6 — 🔴 P0)

**Description :** Le superviseur saisit les informations de l'organisation (raison sociale, adresse, téléphone, email, logo).

**Règles métier :**
- RG-1 : Ces informations sont stockées dans `tenants` pour le tenant courant.
- RG-2 : Le logo est stocké sur le système de fichiers (chemin dans `tenants.logo_chemin`) — pas de blob en base.
- RG-3 : Seul le superviseur peut modifier la structure.

---

### 5.7 Accueil post-login (écran 0.2 — 🔴 P0)

**Description :** Après connexion, affichage de la liste des courriers à traiter de l'agent avec coloration par échéance. Lecture seule — le traitement se fait dans les Corbeilles.

**Règles métier :**
- RG-1 : Couleur selon `date_limite` :
  - Noir : `date_limite < today`.
  - Rouge dégradé (clair → foncé) : `date_limite − today ∈ [0..4 jours]` — plus c'est proche, plus c'est foncé.
  - Vert : `date_limite > today + 4` ou `date_limite IS NULL`.
- RG-2 : Si aucun courrier à traiter, afficher « Néant ».
- RG-3 : Ce composant de coloration est réutilisé dans les listes de corbeilles (PRD-06).

*Note : cet écran affiche des données GEC mais sa logique d'authentification et de routage appartient au socle.*

---

### 5.8 Navigation / droits d'accès UI (écran 0.3 — 🔴 P0)

**Description :** La sidebar/nav affiche uniquement les entrées accessibles au rôle de l'agent connecté.

**Règles métier :**
- RG-1 : Les agents `archiviste` et `agent_standard` ne voient **pas** : Agents, Départements, Sauvegarde, Paramètres mail.
- RG-2 : Le frontend valide le rôle depuis le JWT décodé. Le backend re-vérifie systématiquement.
- RG-3 : Accéder à une route interdite retourne HTTP 403 (pas une redirection silencieuse).

---

### 5.9 Audit log (technique — toutes actions sensibles)

**Description :** Table `audit_log` append-only. Toute action sensible y inscrit une ligne.

**Actions à logger dans ce PRD :**

| Action                   | `entite`     | Déclencheur                                      |
|--------------------------|--------------|--------------------------------------------------|
| `login`                  | `agents`     | Connexion réussie                                |
| `login_echec`            | —            | Tentative échouée (payload : login tenté)        |
| `logout`                 | `agents`     | Déconnexion explicite                            |
| `agent.create`           | `agents`     | Création d'un agent par le superviseur           |
| `agent.update`           | `agents`     | Modification d'un agent                          |
| `agent.desactiver`       | `agents`     | Désactivation                                    |
| `agent.password_change`  | `agents`     | Changement de mot de passe (par soi ou superviseur) |
| `departement.create`     | `departements` | Création                                        |
| `departement.update`     | `departements` | Modification                                   |
| `structure.update`       | `tenants`    | Modification des infos organisation              |

---

## 6. Critères d'acceptation

| ID    | Critère                                                                                              | Type      |
|-------|------------------------------------------------------------------------------------------------------|-----------|
| CA-01 | `POST /api/auth/login` avec credentials valides retourne JWT 200 + `role` correct.                   | Pytest    |
| CA-02 | `POST /api/auth/login` avec mauvais mot de passe retourne HTTP 401, message générique.               | Pytest    |
| CA-03 | Agent `actif = FALSE` → HTTP 401 à la connexion.                                                     | Pytest    |
| CA-04 | Route protégée sans token → HTTP 401.                                                                | Pytest    |
| CA-05 | Route superviseur accédée avec token `archiviste` → HTTP 403.                                        | Pytest    |
| CA-06 | **Isolation tenant** : agent du tenant A ne peut pas lire/modifier les agents du tenant B.           | Pytest    |
| CA-07 | Création d'un agent avec login existant dans le même tenant → HTTP 409.                              | Pytest    |
| CA-08 | Désactivation d'un agent → il ne peut plus se connecter.                                             | Pytest    |
| CA-09 | Connexion réussie inscrit une ligne `audit_log` avec `action='login'`, `tenant_id`, `agent_id`, `ip`. | Pytest   |
| CA-10 | Échec connexion inscrit `action='login_echec'` sans `agent_id` (non identifié).                      | Pytest    |
| CA-11 | Un département lié à des agents actifs ne peut pas être supprimé (HTTP 409 explicite).               | Pytest    |
| CA-12 | Écran `/login` : message d'erreur affiché, sans indication si le login existe.                       | Manuel    |
| CA-13 | Sidebar : un `agent_standard` ne voit pas « Agents », « Départements », « Sauvegarde ».              | Manuel    |
| CA-14 | Superviseur crée un agent, l'agent peut se connecter immédiatement.                                  | Manuel    |
| CA-15 | Superviseur désactive un agent, l'agent voit « Identifiants invalides » à la prochaine tentative.    | Manuel    |

## 7. Contraintes techniques

- **Hachage** : bcrypt avec `rounds ≥ 12`.
- **JWT** : algorithme HS256, secret via `JWT_SECRET` (variable d'env, ≥ 32 octets). Payload minimal : `sub` (agent_id), `tid` (tenant_id), `role`, `exp`.
- **Multi-tenant** : `tenant_id` extrait du JWT uniquement. Jamais en query param ni en body.
- **Async** : toutes les routes FastAPI sont `async def`. Appels bcrypt via `run_in_executor` pour ne pas bloquer la boucle.
- **Audit** : écriture `audit_log` en arrière-plan (fire-and-forget) pour ne pas ralentir la réponse.
- **CORS** : origines autorisées via `ALLOWED_ORIGINS` (variable d'env, virgule-séparées). Helper `Settings.allowed_origins_list` côté backend.
- **Soft delete** : `agents.actif = FALSE` plutôt que suppression physique.
- **`auth_provider`** : colonne réservée sur `agents` (`'local'` par défaut, `'ldap'` v2). Voir `docs/schema.md §1`.
- **Calcul de coloration des échéances** : déporté dans un service partagé (`backend/services/echeances.py` + helper `frontend/lib/echeance-color.ts`) car réutilisé par l'accueil (5.7) et les corbeilles (PRD-06).

## 8. API endpoints

| Méthode | Route                           | Rôles autorisés              | Description                                  |
|---------|---------------------------------|------------------------------|----------------------------------------------|
| POST    | `/api/auth/login`               | Public                       | Authentification, retourne JWT               |
| POST    | `/api/auth/logout`              | Tout agent connecté          | Déconnexion (côté client, log serveur)       |
| GET     | `/api/agents/me`                | Tout agent connecté          | Profil de l'agent connecté                   |
| PUT     | `/api/agents/me`                | Tout agent connecté          | Modifier son propre profil (email, tel, photo, mdp) |
| GET     | `/api/agents`                   | superviseur                  | Lister tous les agents du tenant             |
| POST    | `/api/agents`                   | superviseur                  | Créer un agent                               |
| GET     | `/api/agents/{id}`              | superviseur                  | Détail d'un agent                            |
| PUT     | `/api/agents/{id}`              | superviseur                  | Modifier un agent                            |
| POST    | `/api/agents/{id}/desactiver`   | superviseur                  | Désactiver un agent                          |
| GET     | `/api/departements`             | Tout agent connecté          | Lister les départements du tenant            |
| POST    | `/api/departements`             | superviseur                  | Créer un département                         |
| PUT     | `/api/departements/{id}`        | superviseur                  | Modifier un département                      |
| DELETE  | `/api/departements/{id}`        | superviseur                  | Désactiver si aucun agent actif              |
| GET     | `/api/structure`                | Tout agent connecté          | Infos organisation du tenant                 |
| PUT     | `/api/structure`                | superviseur                  | Modifier la structure                        |
| GET     | `/api/audit-log`                | superviseur                  | Consulter les logs d'audit (paginé, filtrable) |

## 9. Modèle de données impacté

Tables concernées (DDL complet dans `docs/schema.md`) :

- `tenants` : `raison_sociale`, `adresse`, `telephone`, `email`, `logo_chemin`.
- `roles` : référentiel statique seedé par migration (`superviseur`, `archiviste`, `agent_standard`).
- `departements` : créés et gérés par ce module.
- `agents` : entité centrale de ce module.
- `audit_log` : append-only, alimenté par ce module et tous les modules suivants.

Migration Alembic **001** à créer (cf. `docs/schema.md §8`) :
1. Extensions (`pgcrypto`, `pg_trgm`, `unaccent`, `vector`) + configuration FTS `french_unaccent`.
2. `roles`, `types_correspondant`.
3. `tenants`.
4. `departements`, `agents` (avec `auth_provider` et contraintes CHECK).
5. `audit_log`.
6. Seed : rôles statiques (`superviseur`, `archiviste`, `agent_standard`), types correspondant (`personne_physique`, `personne_morale`), tenant de test, agent superviseur initial.

Variables d'environnement utilisées par ce module : `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`, `ALLOWED_ORIGINS`, `MASTER_KEY` (pour le chiffrement futur des mots de passe SMTP/IMAP du tenant — déjà dans `tenants.smtp_password_enc`).

## 10. Dépendances inter-modules

- Requiert : PRD-00 (décisions d'architecture, schéma initial).
- Requis par : tous les autres PRD (PRD-02 à PRD-08) — le JWT produit ici est la porte d'entrée de toute l'application.

## 11. Risques & points ouverts

| Risque / Question ouverte                                    | Probabilité | Impact | Mitigation / décision                                                        |
|--------------------------------------------------------------|-------------|--------|-------------------------------------------------------------------------------|
| Brute-force sur `/api/auth/login`                            | Moyenne     | Élevé  | Reporté à **PRD-09 (Hardening sécurité)** : rate-limiting via `slowapi` + protection IP. En PRD-01 : log systématique de chaque `login_echec` dans `audit_log` avec IP pour analyse a posteriori. |
| Token JWT non révocable en cas de désactivation d'un agent  | Faible      | Moyen  | Vérification `actif` à chaque requête via `get_current_agent`. TTL court (8h).|
| Rotation de `JWT_SECRET` invalide tous les tokens existants | Faible  | Moyen  | Acceptable en v1 ; v2 peut implémenter refresh tokens.                       |
| LDAP prévu v2 : structure `agents` compatible ?             | —           | Faible | Colonne `auth_provider VARCHAR(16) NOT NULL DEFAULT 'local'` ajoutée dans `agents` (cf. `docs/schema.md §1`). Contrainte CHECK autorise `'local' \| 'ldap'`. PRD-09 implémentera l'adaptateur LDAP. |
| Photo avatar : taille et format non contraints              | Moyenne     | Faible | Limiter à 2 Mo, formats JPEG/PNG/WEBP côté API.                               |

## 12. Jalons

| Jalon                                    | Critère de validation                                       | Date cible |
|------------------------------------------|-------------------------------------------------------------|------------|
| Migration Alembic 001 OK                 | `alembic upgrade head` sans erreur sur Postgres 16         | Sprint 1   |
| Routes Auth + Agents vertes              | `pytest tests/test_auth.py tests/test_agents.py -q` → 0 fail | Sprint 1   |
| Isolation tenant vérifiée                | Test dédié : agent tenant A ne lit pas agent tenant B       | Sprint 1   |
| Frontend `/login` + sidebar RBAC         | Démo : 3 rôles testés, menus corrects                      | Sprint 2   |
| Écrans 4.3, 4.4, 4.5, 4.6 navigables    | Superviseur crée un agent, se connecte avec ce compte      | Sprint 2   |
