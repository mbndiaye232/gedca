# Écrans à reproduire — GEDCA

Inventaire dérivé du guide d'utilisation (`docs/guidesoftgedca.pdf`) et des deux vidéos de présentation. Chaque écran est tagué par module, priorité MVP, et dépendances.

**Légende priorité** :
- 🔴 **P0** — bloquant, fait partie du MVP socle ou d'un module en cours.
- 🟠 **P1** — important, à livrer avec le module concerné.
- 🟡 **P2** — peut attendre une itération ultérieure.
- ⚪ **P3** — confort, optionnel.

---

## 0. Socle transverse

### 0.1 🔴 Connexion (`/login`)
- Champs : login, mot de passe.
- Message d'erreur clair en cas d'échec, sans révéler si le login existe.
- Redirige vers `/accueil` après succès.
- Dépend de : aucun.

### 0.2 🔴 Accueil après login (`/accueil`)
- Affiche la liste des courriers à traiter de l'agent connecté avec **coloration** :
  - Noir : `date_limite < today`.
  - Rouge dégradé (clair → foncé) : `date_limite − today ∈ [0..4 jours]` (plus c'est proche, plus c'est foncé).
  - Vert : `date_limite > today + 4` ou `date_limite IS NULL`.
- Affichage informatif uniquement, pas d'action (renvoie vers `Corbeilles` pour traiter).
- Si aucun courrier : message « Néant ».
- Dépend de : 0.1, courriers en base.

### 0.3 🔴 En-tête / navigation latérale
- Menu déroulant ou sidebar avec les sections : Courriers, Documents, Archivage, Corbeilles, Correspondants, Agents, Structure, Paramètres mail, Sauvegarde, Statistiques.
- Désactivation des entrées non autorisées selon le rôle (les non-superviseurs n'ont pas accès aux agents, départements, sauvegarde, paramètres mail).
- Affichage du nom de l'agent connecté + bouton déconnexion.

### 0.4 🟠 Profil agent (lecture / édition de son propre compte)
- Modifier email, téléphone, photo, mot de passe.

---

## 1. Module GEC — Courriers

### 1.1 🔴 Enregistrer un courrier (`/courriers/nouveau`)
- Champs principaux (l'UI s'adapte au sens choisi) :
  - Type / sens : `entrant` | `sortant` | `interne` (radio ou tabs).
  - Référence courrier (texte libre).
  - Catégorie (combo + bouton « + » pour ajouter à la volée).
  - Objet (texte multi-ligne).
  - Type de correspondant (`personne_physique` | `personne_morale`) — visible pour entrant / sortant uniquement.
  - Correspondant (combo filtré par type + bouton « + »).
  - Date du courrier (date du jour par défaut).
  - Sélection du fichier joint (drag & drop + bouton).
  - Date limite de traitement (case à cocher + champ date).
  - Date d'arrivée.
  - Mots-clés.
  - Case « À faire valider » (sortant uniquement).
  - Destinataire : département (combo) → agent (combo filtré). Par défaut, l'agent connecté.
- Bouton « Valider » → enregistre, déclenche notification email au destinataire.
- Le fichier est chiffré et copié dans le stockage géré.
- Dépend de : table `documents`, table `correspondants`, table `departements`, `agents`, chiffrement.

### 1.2 🔴 Corbeilles (`/corbeilles`)
- Affiche les 8 corbeilles de l'agent connecté, avec compteur pour chacune :
  - `A traiter`, `Traités`, `En copie`, `En retard`, `A valider`, `Validés`, `A faire valider`, `En validation`.
- Bouton loupe par corbeille pour ouvrir la liste détaillée.
- Dépend de : courriers, vues corbeilles.

### 1.3 🔴 Liste d'une corbeille (`/corbeilles/:corbeille`)
- Tableau triable : Date, Objet, Correspondant / Agent, Date limite, Statut.
- Coloration des lignes comme dans 0.2.
- Sélection d'un courrier puis bouton « Traiter » → 1.4.
- Dépend de : 1.2.

### 1.4 🔴 Fenêtre de traitement d'un courrier (modal ou `/courriers/:id/traiter`)
- Affiche les métadonnées du courrier.
- Liste des **actions disponibles** (filtrées selon le statut courant) :
  - `Faire une copie` — sélectionner plusieurs agents.
  - `Imputer` — sélectionner un seul agent. ⚠ transfère la propriété, l'imputeur passe en copie.
  - `Demander une validation` — sélectionner un agent validateur + commentaire.
  - `Notes` — ajouter une note (post-it).
  - `Répondre` — ouvre 1.5.
  - `Valider` — uniquement si en demande de validation.
  - `Envoyer` — clôture (courrier passe en `Traités`).
  - `Ajouter un document` — joindre une pièce supplémentaire.
  - `Afficher les documents` — liste avec bouton « Ouvrir ».
  - `Consulter les notes` — liste chronologique des post-it.
  - `Consulter l'historique` — affiche `historiques_courrier` avec nom/fonction des agents et dates.
- Si action non applicable → message d'erreur explicite, pas de blocage muet.
- Dépend de : tables `courriers`, `notes_courrier`, `historiques_courrier`, `imputations`, `demandes_validation`.

### 1.5 🟠 Sous-fenêtre « Répondre » (modal)
- Mêmes champs qu'enregistrement courrier (sens forcé à `sortant`), avec `courrier_origine_id` pré-rempli.
- Case « À faire valider ».

### 1.6 🟠 Rechercher des courriers (`/courriers/recherche`)
- Critères : objet, mots-clés, date (intervalle), correspondant.
- Tableau de résultats avec bouton « Ouvrir le document » et bouton « Consulter le courrier d'origine » (si réponse).
- Filtrage par les droits : un agent ne voit que ses courriers + ceux où il est en copie.

### 1.7 🟠 Modifier un courrier
- Réservé au créateur ou au superviseur.
- Champs identiques à 1.1.

### 1.8 🟡 Supprimer un courrier
- Réservé au superviseur.
- Confirmation obligatoire.
- Soft delete (`supprime = TRUE`) + cascade soft sur notes, copies, historique préservé.

### 1.9 🟠 Redirection (`/redirections`)
- Créer une redirection : choisir département + agent cible.
- Liste de la redirection active (max 1 par agent).
- Bouton supprimer la redirection avec confirmation.
- Dépend de : `redirections`.

### 1.10 🟡 Job d'alerte retard
- Pas un écran, mais un cron Celery quotidien (paramétrable par tenant).
- Envoie un mail au propriétaire de chaque courrier dont `date_limite ≤ today + 4` et qui n'a pas reçu d'alerte du jour.

---

## 2. Module GED — Documents

### 2.1 🔴 Ajouter un document (`/documents/nouveau`)
- Champs : titre, catégorie (obligatoire, combo + « + »), fichier, date du document, mots-clés, résumé, thématique, type de document.
- Case « Document physique associé » → affiche l'arborescence d'archivage pour choisir un sous-dossier (réutilise 3.7 en modal). Bouton « Désélectionner ».
- Bouton Valider.
- Dépend de : chiffrement, OCR worker.

### 2.2 🟠 Ajouter les documents d'un dossier (`/documents/lot`)
- Sélection d'un dossier sur le poste (input directory).
- Catégorie unique appliquée à tous les fichiers.
- Sous-dossier physique unique appliqué à tous (optionnel).
- Barre de progression d'ingestion.
- À l'issue, lien pour aller corriger ce qui doit l'être.

### 2.3 🟠 Ajouter des documents depuis emails (`/documents/imap`)
- Paramètres de recherche : date, mots-clés dans objet / contenu.
- Affichage de la liste des messages trouvés (tableau du haut).
- Affichage des pièces jointes (tableau du bas), filtrées par message sélectionné.
- Bouton « Intégrer dans la GED » → ouvre une mini-fenêtre style 2.1 pré-remplie.
- Dépend de : config IMAP du tenant (table `tenants.smtp_*` étendue avec champs IMAP).

### 2.4 🟠 Modifier un document (`/documents/:id/edit`)
- Tous les champs de 2.1 modifiables.
- Historique des versions visible.

### 2.5 🔴 Rechercher des documents (`/documents`)
- Filtres : titre, mots-clés, contenu (texte OCR), date, catégorie, thématique, type.
- Recherche : double moteur (FTS + sémantique) avec un seul champ unifié + filtres.
- Résultats : tableau avec aperçu (vignette si possible).
- Boutons : Ouvrir (visionneuse), Modifier, Détail emplacement physique, Supprimer (superviseur).

### 2.6 🔴 Visionneuse de document (modal ou `/documents/:id/visionneuse`)
- Affichage PDF inline (react-pdf) — déchiffrement à la volée via stream.
- Pour les autres formats : téléchargement temporaire avec ouverture native.
- À la fermeture du modal, le buffer côté serveur est libéré.

### 2.7 🟠 Détail emplacement physique d'un document (modal)
- Affiche les libellés Site / Local / Rayon / Boîte / Dossier / Sous-dossier avec leurs codes.
- Lecture seule.

### 2.8 🟡 Supprimer un document
- Réservé au superviseur.
- Confirmation + vérification qu'aucun courrier ni sous-dossier n'y est lié.

---

## 3. Module Archivage physique

### 3.1 🔴 Gestion des sites (`/archivage/sites`)
- Tableau éditable inline : numéro (lecture seule, auto), libellé, description.
- Bouton « Actualiser » force le rafraîchissement des numéros.
- Création : saisie d'un libellé, validation au changement de ligne.

### 3.2 🔴 Gestion des locaux / salles (`/archivage/locaux`)
- Combo site en haut (filtre).
- Tableau idem 3.1.
- Bouton « Tout afficher » désactive le filtre.

### 3.3 🔴 Gestion des rayons (`/archivage/rayons`)
- Combos cascade : site → local.
- Tableau.

### 3.4 🔴 Gestion des boîtes (`/archivage/boites`)
- Combos cascade : site → local → rayon.
- Tableau (jusqu'à 999 boîtes par rayon).

### 3.5 🔴 Gestion des dossiers (`/archivage/dossiers`)
- Combos cascade : site → local → rayon → boîte.
- Tableau.

### 3.6 🔴 Gestion des sous-dossiers (`/archivage/sous-dossiers`)
- Combos cascade complets.
- Tableau.

### 3.7 🟠 Sélecteur d'emplacement (composant réutilisable)
- Modal cascade utilisable depuis 1.1, 2.1, 2.4 pour choisir un sous-dossier d'archivage.
- Possibilité de chercher par code (`05.02.03.001.04.07`) ou par libellé.

### 3.8 🟡 Vue arborescente (`/archivage/arbre`)
- Vue tree complète Site → Sous-dossier.
- Recherche dans l'arbre.

---

## 4. Référentiels & administration

### 4.1 🔴 Liste des correspondants (`/correspondants`)
- Tableau filtrable par type, recherche full text sur nom / raison sociale.
- Boutons : Ajouter, Modifier, (Désactiver).

### 4.2 🔴 Ajouter / Modifier un correspondant (modal)
- Sélection du type → affichage des champs adaptés.
- Personne physique : civilité, nom, prénom, fonction, adresse, téléphone, email.
- Personne morale : raison sociale, adresse, téléphone, email.

### 4.3 🔴 Liste des agents (`/agents`) — superviseur uniquement
- Tableau : login, nom, prénom, département, rôle, actif.
- Boutons Ajouter / Modifier / Désactiver.

### 4.4 🔴 Ajouter / Modifier un agent (modal) — superviseur
- Login (unique tenant), mot de passe initial, nom, prénom, email, téléphone, fonction, département, rôle, photo.
- L'app desktop liait à un « groupeware » externe ; en web on gère directement.

### 4.5 🔴 Gestion des départements (`/departements`) — superviseur
- Tableau simple libellé.

### 4.6 🔴 Structure / organisation (`/structure`) — superviseur
- Raison sociale, adresse, téléphone, email, logo.

### 4.7 🔴 Paramètres mail (`/parametres-mail`) — superviseur
- Champs SMTP : host, port, user, password, from, use_tls.
- Champs IMAP (pour 2.3) : host, port, user, password, folder.
- Bouton « Tester l'envoi » et « Tester la connexion IMAP ».

### 4.8 🟡 Gestion des catégories / thématiques / types (`/referentiels`) — superviseur
- Tableaux simples.

---

## 5. Statistiques

### 5.1 🟠 Statistiques par catégorie (`/stats/categories`)
- Sélection période (du / au).
- Graphique barres + tableau.

### 5.2 🟠 Statistiques par agent (`/stats/agents`)
- Sélection période.
- Tableau : nombre de courriers traités par agent.

### 5.3 🟡 Tableau de bord global (`/stats`)
- KPIs : nombre de courriers en cours, en retard, traités ce mois, documents ingérés ce mois, etc.

---

## 6. Sauvegarde

### 6.1 🟡 Sauvegarde de la base (`/sauvegarde/base`) — superviseur
- Bouton déclenchant un job Celery `pg_dump` vers le dossier de sauvegarde paramétré.
- Affichage de la liste des sauvegardes précédentes (auto-incrémentées).

### 6.2 🟡 Sauvegarde des documents (`/sauvegarde/documents`) — superviseur
- Sélection du dossier cible (champ texte côté on-prem, fixe côté SaaS).
- Job Celery qui copie le dossier des fichiers chiffrés.

---

## 7. Spécifiques IA (au-delà de l'app desktop)

### 7.1 🟡 Suggestions de classification (composant)
- Lors d'un upload, le worker propose une catégorie / thématique / type / mots-clés.
- L'archiviste valide ou corrige avant enregistrement définitif.

### 7.2 🟡 Recherche unifiée transverse (`/recherche`)
- Un seul champ qui interroge courriers + documents + correspondants.
- Score combiné FTS + sémantique.

### 7.3 🟡 Assistant RAG (`/assistant`)
- Chat libre sur le corpus du tenant.
- Citations obligatoires (lien vers le document source).

---

## Tableau de dépendances entre modules pour le MVP

```
 Auth (0.1)
   ↓
 Agents + Départements + Structure (4.3, 4.5, 4.6)
   ↓
 Référentiels (Correspondants, Catégories) (4.1, 4.2, 4.8)
   ↓
 ┌────────────────┬──────────────────┐
 ↓                ↓                  ↓
 Documents        Archivage physique  GEC
 (2.1, 2.5, 2.6)  (3.1 → 3.6)         (1.1, 1.2, 1.3, 1.4)
   ↓                                  ↓
 Sélecteur emplacement (3.7)         Redirection (1.9)
                                      Alertes retard (1.10)
```

---

## Inventaire des écrans MVP (P0 + P1)

**P0 absolument indispensables** : 0.1, 0.2, 0.3, 1.1, 1.2, 1.3, 1.4, 2.1, 2.5, 2.6, 3.1–3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7.

**P1 à livrer avec le module** : 0.4, 1.5, 1.6, 1.7, 1.9, 1.10, 2.2, 2.3, 2.4, 2.7, 3.7, 5.1, 5.2.

**P2 à différer** : 1.8, 2.8, 3.8, 4.8, 5.3, 6.1, 6.2, 7.1, 7.2, 7.3.

Total écrans MVP : ~30 écrans, ~10 modaux/composants partagés.
