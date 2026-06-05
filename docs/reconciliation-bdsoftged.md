# Réconciliation schéma GEDCA ↔ base WinDev / HyperFile d'origine

Document de traçabilité — mémoire du projet. Pour chaque table de la base d'origine `softged` (cf. `docs/dumpbdsoftged.txt`), on indique son équivalent dans le schéma PostgreSQL GEDCA et les divergences éventuelles.

## 1. Mapping table par table

### Identités et organisation

| Table d'origine | Équivalent GEDCA | PRD | Notes |
|---|---|---|---|
| `agents` | `agents` | PRD-01 | `npriv (INT)` → `role_id` (FK vers `roles`). Ajout v1 de `cellulaire` et `adresse` (migration 002). Photo : chemin uniquement (pas de BLOB). |
| `Departement` | `departements` | PRD-01 | Ajout `tenant_id`. |
| `structur` | Embarqué dans `tenants` | PRD-01 | PK originale `IDSalon` (résidu d'un copier-coller WinDev). Champs fusionnés : `raison_sociale`, `adresse`, `tel`, `email`, `logo_chemin`. |

### Référentiels

| Table d'origine | Équivalent GEDCA | PRD | Notes |
|---|---|---|---|
| `typeexpediteur` | `types_correspondant` | PRD-01 | Seedé statique : `personne_physique`, `personne_morale`. |
| `categories` | `categories` | PRD-02 | Par tenant, unique sur (`tenant_id`, `libelle`). |
| `type` | **Fusionné dans l'ENUM `sens_courrier`** sur `courriers.sens` | PRD-06 | Valeurs originales : `entrant`, `sortant`, `interne` (confirmé). Plus de table dédiée — validation côté DB via ENUM PostgreSQL. |
| `actions` | (À venir) référentiel des actions du workflow GEC | PRD-06 | Seedé statique : `creation`, `imputation`, `copie`, `reponse`, `validation_demandee`, `validation`, `envoi`, `note`, … |
| `statutcourrier` | `statuts_courrier` | PRD-03 | Seedé statique avec les 8 corbeilles. |
| `etatavancement` | `etats_avancement` | PRD-03 | Seedé. |

### Correspondants

| Table d'origine | Équivalent GEDCA | PRD | Notes |
|---|---|---|---|
| `correspondants` | `correspondants` | PRD-02 | Champs `nomrs`, `societe`, `titre`, `tel`, `cel`, `fax`, `adr`, `email` à migrer. Ajout `civilite` et `prenom` séparés pour les personnes physiques. |

### Documents

| Table d'origine | Équivalent GEDCA | PRD | Notes |
|---|---|---|---|
| `documents` | `documents` | PRD-02 | `chnumdocument` → `numero_enregistrement` (numéro métier interne tenant). `contdoc (VARCHAR 65534)` → `texte_ocr (TEXT)`. `chemin` → `chemin_stockage` + `nonce` (AES-GCM). Ajout `checksum_sha256`, `recherche_fts`, `embedding`. Lien physique via table de liaison `documents_sous_dossiers`. |
| `cryptage` | **Pas de table dédiée** — log dans `audit_log` (`action='document.consulter'`) | PRD-02 | L'origine traçait les décryptages dans une table ; on consolide dans le journal d'audit transverse. |

### Archivage physique (6 niveaux)

| Table d'origine | Équivalent GEDCA | PRD | Notes |
|---|---|---|---|
| `Site` | `sites` | PRD-02 (tables vides) / PRD-05 (routes & UI) | `chnumsite` → vue `v_sous_dossiers_code` (code calculé, jamais stocké). |
| `LocalSalle` | `locaux_salles` | idem | Typo originale `LibelleLoàcalSalle` corrigée en `libelle`. |
| `Rayon` | `rayons` | idem | Typo `LiibelleRayon` corrigée. |
| `Boite` | `boites` | idem | `NumOrdre` → `numero` (SMALLINT 1..999). |
| `DossiersClasseurs` | `dossiers_classeurs` | idem | |
| `SousDossiers` | `sous_dossiers` | idem | Lien GED ↔ archivage via table `documents_sous_dossiers` (M:N). |

### Courriers (GEC)

| Table d'origine | Équivalent GEDCA | PRD | Notes |
|---|---|---|---|
| `courriers` | `courriers` | PRD-06 | `idtype` → ENUM `sens` (cf. ci-dessus). `valide (BIT)` → état dérivé de `demandes_validation`. `IDcourriersrepondu` → `courrier_origine_id`. `observations` à ajouter. |
| `copiescourriers` | `copies_courriers` | PRD-06 | M:N agents en copie. |
| `demandevalidation` | `demandes_validation` | PRD-06 | Enrichi : ENUM `statut_validation` (`en_attente`, `valide`, `rejete`), `commentaire`. |
| `notes` | `notes_courrier` | PRD-06 | `libelle` → `contenu`. |
| `historiques` | `historiques_courrier` | PRD-06 | Distinct du `audit_log` transverse — sert à l'affichage utilisateur de l'historique d'un courrier. |
| `redirection` | `redirections` | PRD-06 | Enrichi : `motif`, `tenant_id`, contrainte `un seul actif par agent`. |

### Configuration mail

| Table d'origine | Équivalent GEDCA | PRD | Notes |
|---|---|---|---|
| `paramail_` | Embarqué dans `tenants` (`smtp_*`, `imap_*`) | PRD-03 | L'origine avait POP3+SMTP+IMAP — on garde SMTP (envoi) et IMAP (ingestion). Pas de POP3. Mots de passe chiffrés via clé maître. |

## 2. Divergences délibérées (à garder en mémoire)

| # | Divergence | Justification |
|---|---|---|
| D1 | **`tenant_id` sur toutes les tables métier** | Multi-tenant SaaS — l'app d'origine est mono-organisation. |
| D2 | **`role_id` + table `roles` au lieu de `agents.npriv (INT)`** | Lisibilité du RBAC + référentiel statique. Codes : `superviseur`, `archiviste`, `agent_standard`. |
| D3 | **`audit_log` transverse** | Remplace partiellement `historiques` (côté admin) et `cryptage` (côté trace). `historiques_courrier` est préservé pour l'historique utilisateur du courrier. |
| D4 | **`paramail_` et `structur` fusionnés dans `tenants`** | Évite des tables-singleton inutiles. `tenants.IDSalon` (PK originale de `structur`) n'est pas reproduite — c'était un résidu de projet WinDev. |
| D5 | **`documents.IDcourriers` (1:N) → `documents_courrier` (M:N) + `courriers.document_principal_id`** | Le guide montre qu'un document peut être pièce principale d'un courrier ET joint à un autre. M:N + un FK dédié pour la pièce principale. |
| D6 | **`chnumXXX` → vue `v_sous_dossiers_code` (code dérivé)** | Évite la désynchronisation entre code stocké et hiérarchie réelle (renommage / réorganisation). |
| D7 | **Photo agent et logo organisation → chemin de fichier** | Conforme à la règle « pas de blob en base » (PRD-02 §7). L'origine stockait en `LONGVARBINARY`. |
| D8 | **`type` (table) → ENUM `sens_courrier`** | Validation au niveau PostgreSQL. Valeurs strictes : `entrant`, `sortant`, `interne`. |
| D9 | **Chiffrement AES-256-GCM + clé HKDF par tenant** | L'origine avait un cryptage maison (probablement XOR ou Base64 obfusqué). On standardise avec une primitive éprouvée. |
| D10 | **`alerte` quotidienne idempotente via table `alertes_envoyees`** | L'origine avait `courriers.datealerte` (une seule alerte par courrier ?) — on précise « une par jour par agent par type ». |

## 3. Renumérotation des migrations Alembic

À la suite de la décision d'ajouter `agents.cellulaire` et `agents.adresse` en migration 002 :

| Migration | Contenu | PRD |
|---|---|---|
| `001_socle.py` | Tenants, agents, départements, audit_log + référentiels statiques | PRD-01 |
| **`002_complements_prd01.py`** | **`ALTER TABLE agents` : `cellulaire`, `adresse`** | **PRD-01 (complément)** |
| `003_stockage.py` | Categories, thématiques, types_document, documents, document_versions + tables archivage vides + statuts_courrier + etats_avancement | PRD-02 |
| `004_ingestion.py` | `ALTER tenants` IMAP + `imap_pieces_jointes` | PRD-03 |
| `005_gec.py` | Courriers, copies, imputations, validations, notes, historiques, redirections, alertes | PRD-06 |

PRD-00 §6 sera mis à jour pour refléter cette nouvelle numérotation.

## 4. Questions tranchées dans cette analyse

- ✅ **`type`** = sens du courrier (entrant/sortant/interne) → fusionné dans l'ENUM `sens`.
- ✅ **Migration 002** = compléments PRD-01 (cellulaire + adresse).
