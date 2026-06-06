# PRD-05 — Module Archivage physique (6 niveaux)

| Champ        | Valeur                                                          |
|--------------|-----------------------------------------------------------------|
| **ID**       | PRD-05                                                          |
| **Module**   | Archivage physique                                              |
| **Statut**   | Approuvé                                                        |
| **Auteur**   | mbndiaye232                                                     |
| **Date**     | 2026-06-05                                                      |
| **Dépend de**| PRD-01 (Auth & RBAC), PRD-02 (table `documents`, tables archivage déjà créées vides en migration 003) |

---

## 1. Contexte & problème

Le guide d'origine (§ XI) décrit un dispositif d'archivage physique organisé en **6 niveaux** hiérarchiques avec une **codification dotée auto-générée** (`SS.LL.RR.BBB.DD.SD`). Chaque document GED peut être lié à un sous-dossier physique, ce qui permet de retrouver instantanément l'emplacement matériel correspondant.

Les tables PostgreSQL sont créées vides en migration 003 (décision Phase A). Ce PRD livre :
- Les routes API CRUD pour les 6 niveaux.
- L'attribution automatique des `numero` au sein de chaque parent (jamais saisis par l'utilisateur).
- Les 6 écrans de gestion (un par niveau, conformes à l'app d'origine).
- Le **sélecteur réutilisable** invoqué depuis l'upload de document pour lier un sous-dossier.

## 2. Objectifs

- OBJ-1 : Permettre au superviseur et à l'archiviste de gérer la hiérarchie d'emplacements physiques (CRUD 6 niveaux).
- OBJ-2 : Garantir l'unicité et la séquentialité des `numero` au sein de chaque parent (jamais de trou éditable par l'utilisateur).
- OBJ-3 : Fournir un endpoint qui renvoie le code complet `SS.LL.RR.BBB.DD.SD` + les libellés intermédiaires pour un sous-dossier donné.
- OBJ-4 : Composant frontend réutilisable permettant à un archiviste de choisir un sous-dossier via une cascade Site → … → Sous-dossier, intégré dans l'upload de document.
- OBJ-5 : Empêcher la suppression d'un niveau qui contient encore des enfants (HTTP 409 explicite).

## 3. Non-objectifs (hors périmètre)

- QR codes / codes-barres sur les emplacements (différé v2).
- Prêts / retours de documents physiques (différé v2).
- Recensement / récolement automatique (différé).
- Renommage en masse / déplacement d'arborescence (manipulation à risque, hors v1).

## 4. Utilisateurs cibles

| Rôle             | Ce qu'ils font dans ce module                                              |
|------------------|----------------------------------------------------------------------------|
| `superviseur`    | Crée et organise toute la hiérarchie. Supprime les emplacements vides.     |
| `archiviste`     | Crée, renomme, et lie des documents à un sous-dossier lors de l'upload.    |
| `agent_standard` | Lecture seule : voit l'emplacement physique d'un document (détail).        |

## 5. Fonctionnalités

### 5.1 Gestion des sites (écran 3.1 — 🔴 P0)

**Description :** Tableau des sites du tenant courant. CRUD inline.

**Règles métier :**
- RG-1 : `numero` auto-attribué = `MAX(numero) + 1 OVER (PARTITION BY tenant_id) + 1`, capé à 99. Au-delà → HTTP 409.
- RG-2 : `libelle` obligatoire, unique optionnel (pas de contrainte d'unicité — on accepte deux sites de même libellé sur des emplacements différents).
- RG-3 : Suppression bloquée si au moins un `locaux_salles` y est rattaché → HTTP 409.

### 5.2 Gestion des locaux / salles (écran 3.2 — 🔴 P0)

**Description :** Tableau filtré par site. Combo « Site » en haut.

**Règles métier :**
- RG-1 : `numero` auto-attribué au sein du site sélectionné.
- RG-2 : Suppression bloquée si au moins un `rayons` y est rattaché.

### 5.3 Gestion des rayons (écran 3.3 — 🔴 P0)
### 5.4 Gestion des boîtes (écran 3.4 — 🔴 P0) — **3 chiffres, 1 à 999**
### 5.5 Gestion des dossiers (écran 3.5 — 🔴 P0)
### 5.6 Gestion des sous-dossiers (écran 3.6 — 🔴 P0)

Tous suivent la même logique : combos cascade pour filtrer, tableau pour CRUD, auto-numérotation, blocage suppression si enfants présents.

### 5.7 Sélecteur d'emplacement (composant réutilisable — écran 3.7 — 🟠 P1)

**Description :** Modal cascade utilisée depuis :
- `DocumentNouveau` (upload — sélection du sous-dossier physique optionnel)
- `Document` édition (modification du lien)
- `Document` consultation (« Détail emplacement »)

**Règles métier :**
- RG-1 : Cinq combos en cascade : Site → Local → Rayon → Boîte → Dossier → liste des sous-dossiers.
- RG-2 : Champ de recherche par code partiel (`05.02.01` filtre tous les sous-dossiers dont le code commence par `05.02.01.`).
- RG-3 : Le sous-dossier sélectionné est rendu via `onSelect(sousDossierId, codeComplet)`.
- RG-4 : Bouton « Désélectionner » qui appelle `onSelect(null, null)`.

### 5.8 Détail emplacement physique (écran 2.7 — 🟠 P1)

**Description :** Modal lecture seule qui affiche les 6 niveaux avec code et libellé pour un document donné.

**Règles métier :**
- RG-1 : Endpoint `GET /api/sous-dossiers/{id}/code` renvoie `{ code_complet, site: {numero, libelle}, local: {…}, rayon: {…}, boite: {…}, dossier: {…}, sous_dossier: {…} }`.
- RG-2 : Si aucun emplacement → message « Aucun emplacement physique associé ».

## 6. Critères d'acceptation

| ID    | Critère                                                                                  | Type      |
|-------|------------------------------------------------------------------------------------------|-----------|
| CA-01 | Créer un site → `numero = 1`. Créer un 2e → `numero = 2`.                                | Pytest    |
| CA-02 | Tenter de créer un 100e site → HTTP 409 avec message « 99 sites max ».                   | Pytest    |
| CA-03 | Auto-numérotation isolée par tenant (le tenant B repart de 1 même si le tenant A a 5).   | Pytest    |
| CA-04 | Supprimer un site contenant des locaux → HTTP 409.                                       | Pytest    |
| CA-05 | Supprimer un sous-dossier lié à un document → HTTP 409.                                  | Pytest    |
| CA-06 | `GET /api/sous-dossiers/{id}/code` → renvoie `05.02.01.001.04.07` + libellés.            | Pytest    |
| CA-07 | Isolation tenant : `GET /api/sites` ne renvoie pas les sites d'un autre tenant.          | Pytest    |
| CA-08 | Archiviste peut créer/modifier ; agent_standard reçoit 403 sur POST/PUT/DELETE.         | Pytest    |
| CA-09 | UI — Saisie cascade : sélectionner un site filtre les locaux, etc.                       | Manuel    |
| CA-10 | UI — Sélecteur réutilisable depuis l'upload de document : sous-dossier choisi est lié.   | Manuel    |
| CA-11 | UI — Affichage du code complet sur le tableau des sous-dossiers.                         | Manuel    |

## 7. Contraintes techniques

- **Auto-numérotation** : transaction SQL `SELECT COALESCE(MAX(numero), 0) + 1 FROM <table> WHERE <parent_id> = $1 FOR UPDATE` puis `INSERT`. Évite les courses concurrentes via `SERIALIZABLE` ou lock applicatif.
- **Cap supérieur** : sites/locaux/rayons/dossiers/sous-dossiers = 99, boîtes = 999. CHECK en base (déjà posé en migration 003) + validation côté route avec message clair.
- **Vue `v_sous_dossiers_code`** déjà créée en migration 003 — sert pour le code complet.
- **Multi-tenant** : injection automatique via `agent_courant`, jamais en query param.
- **Audit log** : actions `archivage.<niveau>.create | update | delete`.
- **Performance** : index `(parent_id, numero)` déjà posés via UniqueConstraint.

## 8. API endpoints

| Méthode | Route                                       | Rôles autorisés          | Description                                  |
|---------|---------------------------------------------|--------------------------|----------------------------------------------|
| GET     | `/api/archivage/sites`                      | tout connecté            | Liste des sites du tenant                    |
| POST    | `/api/archivage/sites`                      | archiviste, superviseur  | Créer un site (numero auto)                  |
| PUT     | `/api/archivage/sites/{id}`                 | archiviste, superviseur  | Modifier libellé / description               |
| DELETE  | `/api/archivage/sites/{id}`                 | superviseur              | Supprimer (bloqué si enfants)                |
| GET     | `/api/archivage/sites/{id}/locaux`          | tout connecté            | Locaux du site                               |
| POST    | `/api/archivage/locaux`                     | archiviste, superviseur  | Créer un local (body : site_id, libelle)     |
| PUT     | `/api/archivage/locaux/{id}`                | archiviste, superviseur  | Modifier                                     |
| DELETE  | `/api/archivage/locaux/{id}`                | superviseur              | Supprimer                                    |
| GET     | `/api/archivage/locaux/{id}/rayons`         | tout connecté            | Rayons du local                              |
| POST/PUT/DELETE | `/api/archivage/rayons[/{id}]`      | idem                     |                                              |
| GET     | `/api/archivage/rayons/{id}/boites`         | tout connecté            | Boîtes du rayon                              |
| POST/PUT/DELETE | `/api/archivage/boites[/{id}]`      | idem                     |                                              |
| GET     | `/api/archivage/boites/{id}/dossiers`       | tout connecté            | Dossiers de la boîte                         |
| POST/PUT/DELETE | `/api/archivage/dossiers[/{id}]`    | idem                     |                                              |
| GET     | `/api/archivage/dossiers/{id}/sous-dossiers`| tout connecté            | Sous-dossiers du dossier                     |
| POST/PUT/DELETE | `/api/archivage/sous-dossiers[/{id}]` | idem                   |                                              |
| GET     | `/api/archivage/sous-dossiers/{id}/code`    | tout connecté            | Renvoie le code complet + libellés des 6 niveaux |
| GET     | `/api/archivage/recherche?code=05.02.01`    | tout connecté            | Recherche cascade par code partiel (pour le sélecteur) |

## 9. Modèle de données impacté

**Aucune migration nouvelle** — les 7 tables (`sites`, `locaux_salles`, `rayons`, `boites`, `dossiers_classeurs`, `sous_dossiers`, `documents_sous_dossiers`) et la vue `v_sous_dossiers_code` existent déjà depuis la migration 003 (PRD-02).

Modèles SQLAlchemy déjà présents dans `backend/app/models/archivage.py`.

## 10. Dépendances inter-modules

- Requiert : PRD-01 (auth + tenant), PRD-02 (tables créées + lien `documents_sous_dossiers`).
- Requis par : PRD-06 (les courriers pourront référencer des emplacements pour leurs pièces jointes — usage indirect via `documents`).

## 11. Risques & points ouverts

| Risque                                                              | Probabilité | Impact | Mitigation                                                                                  |
|---------------------------------------------------------------------|-------------|--------|---------------------------------------------------------------------------------------------|
| Course concurrente sur l'attribution du `numero`                    | Faible      | Moyen  | Lock SQL `FOR UPDATE` sur la requête `MAX(numero)` ou `SERIALIZABLE` transaction.           |
| Trous dans la séquence après suppression                            | Élevée      | Faible | Acceptable — pas de réutilisation des numéros (cohérent avec l'app d'origine).             |
| Trop de niveaux pour des petits clients                             | Moyenne     | Faible | Aucune obligation de remplir les 6 niveaux : un client peut n'avoir que Site → Boîte.       |
| Renommage d'un libellé casse les codes affichés ailleurs            | Faible      | Faible | Le code numérique reste stable ; seul le libellé change. Vue recalculée à la volée.        |

## 12. Jalons

| Jalon                                            | Critère de validation                                              |
|--------------------------------------------------|--------------------------------------------------------------------|
| Schémas Pydantic + routes backend                | OpenAPI à jour, endpoints accessibles                              |
| Tests pytest archivage verts                     | CA-01 à CA-08 passent                                              |
| 6 écrans frontend navigables                     | Démo : créer un sous-dossier depuis zéro, voir le code calculé     |
| Sélecteur réutilisable intégré dans l'upload     | Lier un document à un sous-dossier depuis l'écran 2.1              |
