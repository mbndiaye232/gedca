# PRD-06A — Module GEC (base) : enregistrement, corbeilles, actions

| Champ        | Valeur                                                                          |
|--------------|---------------------------------------------------------------------------------|
| **ID**       | PRD-06A                                                                         |
| **Module**   | GEC (Gestion Électronique des Courriers) — partie 1/2                           |
| **Statut**   | Brouillon                                                                       |
| **Auteur**   | mbndiaye232                                                                     |
| **Date**     | 2026-06-06                                                                      |
| **Dépend de**| PRD-01 (Auth, agents), PRD-02 (documents pour pièces jointes), PRD-05 (sous-dossier physique optionnel) |
| **Suivi par**| PRD-06B (validation, redirection, alertes, statistiques)                        |

---

## 1. Contexte & problème

L'app desktop d'origine (guide § I + § II) traite le courrier comme l'**espace de travail principal** : chaque agent voit ses courriers dans des « corbeilles » virtuelles et les fait avancer via des actions (imputer, copier, répondre, valider, etc.). Les 3 sens (entrant / sortant / interne) ont chacun leurs spécificités.

PRD-06A couvre le **cœur fonctionnel** :
- L'enregistrement d'un courrier (les 3 sens)
- Les 8 corbeilles avec coloration par échéance
- Les actions de base qui font avancer un courrier sans toucher au workflow de validation
- Les pièces jointes liées au document

PRD-06B couvrira ensuite : workflow validation (à faire valider / à valider / validés / en validation), redirection congés, alertes retard, statistiques.

## 2. Objectifs

- OBJ-1 : Permettre à un agent d'**enregistrer** un courrier en moins de 30 secondes (formulaire compact, valeurs par défaut intelligentes).
- OBJ-2 : Page **Corbeilles** comme espace de travail quotidien, affichant les 8 corbeilles avec compteur dynamique.
- OBJ-3 : Fenêtre **Traiter** unique qui propose contextuellement les actions autorisées selon le statut du courrier.
- OBJ-4 : Actions de base implémentées : **Faire une copie**, **Imputer**, **Répondre**, **Envoyer**, **Ajouter une note**, **Ajouter un document**.
- OBJ-5 : Historique complet des actions sur un courrier (qui, quoi, quand).
- OBJ-6 : Coloration par échéance (noir / rouge dégradé / vert) cohérente avec l'accueil (PRD-01 §5.7).
- OBJ-7 : Pièces jointes : un courrier a une pièce principale + N pièces additionnelles, tous typés `Document` (référentiel unique PRD-02).

## 3. Non-objectifs (différés à PRD-06B)

- Workflow `demander validation` / `valider` / `rejeter` (corbeilles « A valider », « Validés », « A faire valider », « En validation »).
- Redirection d'un agent en congés.
- Alertes retard quotidiennes par email.
- Statistiques par catégorie et par agent.
- Recherche avancée multi-critères transverse aux courriers.
- Récupération de pièces jointes depuis IMAP (PRD-03 §5.8).

## 4. Utilisateurs cibles

| Rôle             | Ce qu'ils font dans ce module                                              |
|------------------|----------------------------------------------------------------------------|
| `superviseur`    | Tout ce que fait un agent + suppression de courriers + administration des références. |
| `archiviste`     | Tout ce que fait un agent. Peut enregistrer des courriers pour autrui.     |
| `agent_standard` | Enregistre ses propres courriers, traite ceux qui lui sont destinés ou imputés, reçoit des copies. |

## 5. Fonctionnalités

### 5.1 Enregistrer un courrier (écran 1.1 — 🔴 P0)

**Description :** Formulaire unique pour les 3 sens. L'UI s'adapte selon le sens choisi (entrant / sortant / interne).

**Champs communs :**
- Sens (radio) : `entrant` | `sortant` | `interne` — défaut : `entrant`
- Catégorie (combo + bouton « + » réutilisant la création à la volée de PRD-02)
- Référence externe (texte libre — celle du courrier d'origine)
- Objet (textarea, obligatoire)
- Date du courrier (par défaut : aujourd'hui)
- Date d'arrivée (entrant uniquement, défaut : aujourd'hui)
- Date limite de traitement (case à cocher + champ date)
- Mots-clés (texte libre)
- Pièce principale (composant `DropZone` + crée un Document via PRD-02)
- Observations (textarea, optionnel)

**Champs spécifiques entrant / sortant :**
- Correspondant (combo filtré par type personne physique / morale, + bouton « + »)

**Champs spécifiques interne :**
- Pas de correspondant — l'expéditeur et le destinataire sont des agents internes.

**Destinataire (tous sens) :**
- Département (combo) → Agent (combo filtré) — défaut : l'agent connecté
- Case « Faire valider avant envoi » → désactivée en PRD-06A (sera activée en PRD-06B)

**Règles métier :**
- RG-1 : Statut initial = `a_traiter`. Le courrier apparaît dans la corbeille « A traiter » du destinataire.
- RG-2 : `numero_enregistrement` auto-attribué : format **`YYYY-NNNNNN`** (ex. `2026-000142`), séquence **reset au 1er janvier**, isolée par tenant. Stocké en base, jamais modifiable.
- RG-3 : Le `agent_proprietaire_id` = agent destinataire choisi (par défaut, l'agent connecté pour un sortant ou un interne envoyé).
- RG-4 : La pièce principale crée un `Document` chiffré (PRD-02) et stocke son `id` dans `courriers.document_principal_id`. **Obligatoire dans tous les cas** (entrant, sortant, interne) — décision PRD-06A. Pas de courrier sans support documentaire.
- RG-5 : Un événement `creation` est inscrit dans `historiques_courrier`.
- RG-6 : **Notification email envoyée au destinataire** dès 06A :
  - Si le tenant a configuré son SMTP, envoi async via Celery (template Jinja).
  - Si non configuré : warning loggué dans `audit_log` (action `courrier.notification_skipped`), aucune erreur visible côté utilisateur.
  - L'envoi ne bloque jamais la création (fire-and-forget).

### 5.2 Page Corbeilles (écran 1.2 — 🔴 P0)

**Description :** L'espace de travail principal. Affiche les 8 corbeilles de l'agent connecté avec un compteur.

**Les 8 corbeilles** (vocabulaire conservé du guide § II.1) :

| # | Code | Libellé | Définition | Couvert dans |
|---|---|---|---|---|
| 1 | `a_traiter` | A traiter | Statut = `a_traiter` ET `agent_proprietaire_id = me` | 06A |
| 2 | `traite` | Traités | Statut = `traite` ET agent connecté est propriétaire ou ancien propriétaire | 06A |
| 3 | `en_copie` | En copie | Présent dans `copies_courriers` pour l'agent connecté | 06A |
| 4 | `en_retard` | En retard | Statut ≠ `traite` ET `date_limite < today` ET (propriétaire OU en copie) | 06A |
| 5 | `a_valider` | A valider | demandes_validation : validateur = me, statut = `en_attente` | **06B** |
| 6 | `valides` | Validés | demandes_validation faite par moi, statut = `valide` (réponse retournée) | **06B** |
| 7 | `a_faire_valider` | A faire valider | Courrier dont je suis propriétaire avec statut = `a_faire_valider` | **06B** |
| 8 | `en_validation` | En validation | demandes_validation faite par moi, statut = `en_attente` | **06B** |

**Affichage :**
- Cartes de corbeilles en haut (3-4 par ligne en desktop) avec icône, libellé, compteur.
- Clic sur une carte → liste détaillée en dessous (sans rechargement de page).
- En PRD-06A, les corbeilles 5-8 sont visibles avec un badge **« Bientôt disponible »** (compteur = 0).

### 5.3 Liste d'une corbeille (écran 1.3 — 🔴 P0)

**Description :** Tableau des courriers de la corbeille sélectionnée.

**Colonnes :**
- Numéro d'enregistrement (mono)
- Sens (icône colorée : ↘ entrant vert, ↗ sortant bleu, ↺ interne violet)
- Objet (tronqué, info-bulle complète au survol)
- Correspondant (ou « — » pour interne)
- Date du courrier
- Date limite (avec badge coloré selon échéance — réutilise `lib/echeance.ts` de PRD-01)
- Statut (badge)
- Actions (bouton « Traiter »)

**Règles métier :**
- RG-1 : Tri par défaut : date limite ascendante (les plus urgents en haut).
- RG-2 : Recherche locale dans la liste (filtre `objet`, `numero_enregistrement`, `correspondant`).
- RG-3 : Pagination 50 par page.

### 5.4 Fenêtre Traiter (écran 1.4 — 🔴 P0)

**Description :** Modal grande largeur qui affiche un courrier et propose les actions disponibles.

**Sections affichées :**
- **En-tête** : numéro, sens, objet, correspondant, date, date limite (badge coloré)
- **Pièces** : pièce principale + pièces additionnelles avec bouton « Ouvrir » (réutilise `Visionneuse` de PRD-02)
- **Actions disponibles** (liste filtrée selon le statut courant) :
  - 🔁 **Faire une copie** (sélection multi-agents)
  - ➡️ **Imputer** (sélection 1 agent)
  - ↩️ **Répondre** (ouvre un mini-formulaire de courrier sortant lié)
  - ✅ **Envoyer** (passe à `traite`)
  - 📎 **Ajouter un document** (uploader une pièce jointe additionnelle)
  - 📝 **Ajouter une note** (post-it)
  - 👁 **Voir les notes** / **Voir l'historique** (toggle d'affichage en bas)
  - (en PRD-06B : Demander une validation, Valider, Rejeter)
- **Notes** (collapsible) : liste des notes du courrier, plus récente en haut.
- **Historique** (collapsible) : timeline des actions (qui, quoi, quand).

**Règles d'autorisation d'action (PRD-06A) :**

| Action | Conditions |
|---|---|
| Faire une copie | Statut ≠ `traite`. Tout agent qui voit le courrier. |
| Imputer | Statut = `a_traiter`. Agent propriétaire uniquement. |
| Répondre | Statut ≠ `traite`. Agent propriétaire ou en copie. Génère un courrier sortant lié via `courrier_origine_id`. |
| Envoyer | Statut = `a_traiter`. Agent propriétaire uniquement. Passe le statut à `traite`. |
| Ajouter un document | Statut ≠ `traite`. Agent propriétaire ou en copie. |
| Ajouter une note | Toujours. Tout agent qui voit le courrier. |

### 5.5 Faire une copie (action — PRD-06A)

**Description :** L'agent met le courrier en copie pour un ou plusieurs autres agents.

**Règles métier :**
- RG-1 : Multi-sélection d'agents du tenant (exclure l'agent courant et les agents déjà en copie).
- RG-2 : Pour chaque agent sélectionné, créer une ligne dans `copies_courriers`.
- RG-3 : Inscrire dans `historiques_courrier` (action `copie`, payload = liste d'agent_id).
- RG-4 : Envoi de notification email à chaque agent en copie (si SMTP tenant configuré).

### 5.6 Imputer (action — PRD-06A)

**Description :** Transfère la propriété du courrier à un autre agent. L'imputeur passe en copie.

**Règles métier :**
- RG-1 : Sélection d'**un seul** agent destinataire (combo départements → agents).
- RG-2 : `agent_proprietaire_id` devient l'agent imputé.
- RG-3 : L'ancien propriétaire est ajouté à `copies_courriers` (s'il n'y est pas déjà).
- RG-4 : Une ligne dans `imputations` est créée (imputeur, imputé, instruction optionnelle, timestamp).
- RG-5 : Inscrire dans `historiques_courrier` (action `imputation`).
- RG-6 : Notification email à l'agent imputé.
- RG-7 : Une fois imputé, le courrier disparaît de la corbeille « A traiter » de l'imputeur et apparaît dans celle de l'imputé.

### 5.7 Répondre (action — PRD-06A)

**Description :** Ouvre un mini-formulaire d'enregistrement de courrier sortant lié au courrier d'origine.

**Règles métier :**
- RG-1 : Sens forcé à `sortant`.
- RG-2 : `courrier_origine_id` = id du courrier d'origine (consultable via bouton « Voir le courrier d'origine » plus tard).
- RG-3 : Correspondant pré-rempli = correspondant du courrier d'origine.
- RG-4 : Objet pré-rempli avec préfixe « Rép : » + objet d'origine.
- RG-5 : À la création de la réponse, le courrier d'origine reste dans l'état actuel — c'est l'action `Envoyer` qui le passe à `traite`.

### 5.8 Envoyer (action — PRD-06A)

**Description :** Clôture le traitement du courrier (passage à `traite`).

**Règles métier :**
- RG-1 : Statut du courrier d'origine devient `traite`.
- RG-2 : Date de clôture stockée dans `historiques_courrier` (action `envoi`).
- RG-3 : En PRD-06B (workflow validation) cette action sera bloquée tant qu'il y a une demande de validation en attente.

### 5.9 Notes (action — PRD-06A)

**Description :** Post-it électronique. Tout agent qui voit le courrier peut ajouter une note.

**Règles métier :**
- RG-1 : Champ texte libre, 1000 caractères max.
- RG-2 : Stocké dans `notes_courrier` avec timestamp + auteur.
- RG-3 : Visible par tous les agents qui voient le courrier (propriétaire, en copie, anciens propriétaires).
- RG-4 : Inscrire dans `historiques_courrier` (action `note`).

### 5.10 Ajouter un document (action — PRD-06A)

**Description :** Joindre une pièce additionnelle à un courrier (en complément de la pièce principale).

**Règles métier :**
- RG-1 : Réutilise `DropZone` + le pipeline d'upload de PRD-02 (chiffrement, déduplication, OCR).
- RG-2 : Crée un lien dans `documents_courrier` (M:N entre courriers et documents).
- RG-3 : Métadonnées simples au minimum (titre = nom du fichier, catégorie = celle du courrier).
- RG-4 : Inscrire dans `historiques_courrier` (action `ajout_document`).

### 5.11 Historique d'un courrier (écran composant — 🔴 P0)

**Description :** Timeline chronologique de toutes les actions effectuées sur un courrier, avec qui, quoi, quand.

**Affichage :**
- Liste descendante (plus récent en haut).
- Pour chaque entrée : icône colorée selon l'action, libellé, agent, date relative + absolue.
- Source : `historiques_courrier` filtrée sur `courrier_id`.

## 6. Critères d'acceptation

| ID    | Critère                                                                                              | Type      |
|-------|------------------------------------------------------------------------------------------------------|-----------|
| CA-01 | Créer un courrier entrant → apparaît dans la corbeille « A traiter » du destinataire.                | Pytest    |
| CA-02 | `numero_enregistrement` auto-séquentiel par tenant, format `YYYY-NNNNNN`.                            | Pytest    |
| CA-03 | Tenant A ne voit aucun courrier du tenant B (isolation tenant).                                      | Pytest    |
| CA-04 | Imputer un courrier : propriétaire change, ancien propriétaire passe en copie, action loggée.        | Pytest    |
| CA-05 | Faire une copie : ajoute N lignes dans `copies_courriers`, le courrier apparaît en corbeille « En copie » des copiés. | Pytest |
| CA-06 | Envoyer : statut passe à `traite`, le courrier sort de « A traiter » et apparaît en « Traités ».    | Pytest    |
| CA-07 | Action `Imputer` bloquée sur statut `traite` → HTTP 409.                                             | Pytest    |
| CA-08 | Notes : un agent_standard en copie peut ajouter une note, elle est visible par tous.                  | Pytest    |
| CA-09 | Répondre : crée un courrier sortant avec `courrier_origine_id` rempli.                                | Pytest    |
| CA-10 | Historique : chaque action crée une entrée datée et signée.                                          | Pytest    |
| CA-11 | UI : page Corbeilles affiche 8 cartes, 4 actives (06A) + 4 « Bientôt disponible ».                  | Manuel    |
| CA-12 | UI : fenêtre Traiter masque les actions non autorisées selon le statut.                              | Manuel    |
| CA-13 | UI : coloration par échéance cohérente avec l'accueil (noir / rouge dégradé / vert).                | Manuel    |
| CA-14 | UI : pièces jointes ouvrent la Visionneuse de PRD-02.                                                | Manuel    |

## 7. Contraintes techniques

- **Multi-tenant** : `tenant_id` injecté via dépendance FastAPI, jamais en query.
- **Audit log** : actions `courrier.create`, `courrier.imputation`, `courrier.copie`, `courrier.envoi`, etc.
- **Concurrence** : 2 agents qui imputent le même courrier en même temps → contrainte applicative (vérification du statut courant avant maj) + retour HTTP 409 explicite.
- **Numérotation auto** : `SELECT ... FOR UPDATE` + `MAX(numero)+1` par tenant et par année (similaire à PRD-05 archivage).
- **Notifications email** : déposées dans une queue Celery en async — pas bloquantes (préparation pour PRD-06B alertes).
- **Performance** : index sur `(tenant_id, agent_proprietaire_id, statut_id)` pour les requêtes corbeilles.

## 8. API endpoints

| Méthode | Route                                       | Rôles               | Description                                  |
|---------|---------------------------------------------|---------------------|----------------------------------------------|
| GET     | `/api/courriers/corbeilles/compteurs`       | tout connecté       | Compteurs des 8 corbeilles de l'agent       |
| GET     | `/api/courriers?corbeille=<code>`           | tout connecté       | Liste des courriers d'une corbeille          |
| GET     | `/api/courriers/{id}`                       | tout connecté + acl | Détail (avec pièces, notes, historique)     |
| POST    | `/api/courriers`                            | tout connecté       | Créer un courrier (multipart : pièce principale + JSON métadonnées) |
| POST    | `/api/courriers/{id}/copies`                | propriétaire+copie  | Mettre des agents en copie                   |
| POST    | `/api/courriers/{id}/imputer`               | propriétaire        | Imputer à un agent (transfert propriété)     |
| POST    | `/api/courriers/{id}/repondre`              | propriétaire+copie  | Créer une réponse (courrier sortant lié)     |
| POST    | `/api/courriers/{id}/envoyer`               | propriétaire        | Clôturer (statut → traite)                   |
| POST    | `/api/courriers/{id}/notes`                 | qui voit le courrier | Ajouter une note                            |
| POST    | `/api/courriers/{id}/documents`             | propriétaire+copie  | Ajouter une pièce jointe (multipart)         |
| GET     | `/api/courriers/{id}/historique`            | qui voit le courrier | Timeline complète                           |
| DELETE  | `/api/courriers/{id}`                       | superviseur         | Soft delete                                  |

## 9. Modèle de données impacté

**Migration Alembic 005_gec_base** :

Tables créées :
- `statuts_courrier` (référentiel statique, seed des 8 statuts)
- `courriers` (cf. `docs/schema.md §5`)
- `copies_courriers`
- `imputations`
- `notes_courrier`
- `historiques_courrier`
- `documents_courrier`

Tables différées à PRD-06B (migration 006) :
- `demandes_validation`
- `redirections`
- `alertes_envoyees`
- `etats_avancement` (référentiel)

## 10. Dépendances inter-modules

- Requiert :
  - PRD-01 (auth, agents, départements, audit log)
  - PRD-02 (documents, catégories, correspondants — la table `correspondants` existe déjà depuis PRD-02 §3)
  - PRD-05 (rien d'obligatoire — un courrier peut référencer une pièce avec sous-dossier physique via le pipeline normal de PRD-02)
- Requis par :
  - PRD-06B (étend les corbeilles avec validation)
  - PRD-07 (statistiques IA pourront analyser les flux de courriers)

## 11. Risques & points ouverts

| Risque                                                              | Probabilité | Impact | Mitigation                                                                                  |
|---------------------------------------------------------------------|-------------|--------|---------------------------------------------------------------------------------------------|
| Course concurrente sur `numero_enregistrement` (2 créations en // ) | Faible      | Moyen  | `SELECT ... FOR UPDATE` + sequence applicative par tenant.                                  |
| Notification email échoue → courrier créé mais destinataire non informé | Moyenne     | Moyen   | Notification async (Celery). Audit log de l'échec. Bandeau « non notifié » sur la fiche.   |
| Imputer un courrier déjà imputé → conflit d'état                    | Faible      | Faible  | Vérifier `agent_proprietaire_id == agent_appelant` avant maj. 409 si non.                  |
| Pièce principale obligatoire ? Sortants peuvent être créés sans     | Confirmé    | —      | **Décision PRD-06A** : pièce principale **obligatoire pour tous les sens** (incluant interne). Pas de courrier « fantôme » dans la GED. |
| Trop de notes = bruit visuel                                        | Moyenne     | Faible  | Limiter affichage initial à 3 notes + bouton « voir tout ».                                |
| Cas de la `numero_enregistrement` au changement d'année             | Confirmé    | —      | Reset à 1 au 1er janvier. `EXTRACT(year FROM NOW())` dans la séquence.                    |

## 12. Jalons

| Jalon                                            | Critère de validation                                              |
|--------------------------------------------------|--------------------------------------------------------------------|
| Migration 005 + modèles SQLAlchemy               | `alembic upgrade head` OK, importable sans erreur                 |
| Routes backend de base                           | Création courrier + imputer + faire copie + envoyer testés via curl |
| Page Corbeilles côté frontend                    | 8 cartes affichées, compteurs dynamiques                          |
| Fenêtre Traiter                                  | Actions contextuelles fonctionnelles                              |
| Tests pytest                                     | CA-01 à CA-10 verts                                              |
| Démo navigable                                   | Création → imputation → réponse → envoi sans rechargement de page |
