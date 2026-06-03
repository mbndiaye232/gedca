# PRD-XX — [Titre court]

<!-- Copier ce fichier, renommer en prd-NN-slug.md, supprimer les commentaires. -->

| Champ        | Valeur                                          |
|--------------|-------------------------------------------------|
| **ID**       | PRD-XX                                          |
| **Module**   | [Socle / GED / GEC / Archivage / IA / Transverse] |
| **Statut**   | `Brouillon` · `En revue` · `Approuvé` · `Livré`  |
| **Auteur**   | [nom]                                           |
| **Date**     | AAAA-MM-JJ                                      |
| **Dépend de**| PRD-NN, PRD-NN                                  |

---

## 1. Contexte & problème

<!-- 3-5 phrases. Pourquoi ce module existe, quel problème utilisateur il résout.
     Citer la section du guide (`docs/guide.txt`) ou les tables HyperFile concernées. -->

## 2. Objectifs

<!-- Ce que ce PRD doit rendre possible une fois livré. -->

- OBJ-1 : …
- OBJ-2 : …

## 3. Non-objectifs (hors périmètre)

<!-- Ce qui est explicitement exclu pour éviter le scope creep. -->

- …

## 4. Utilisateurs cibles

| Rôle              | Ce qu'ils font dans ce module                  |
|-------------------|------------------------------------------------|
| `superviseur`     | …                                              |
| `archiviste`      | …                                              |
| `agent_standard`  | …                                              |

## 5. Fonctionnalités

<!-- Sections 5.N numérotées, correspondant chacune à un écran ou un comportement.
     Référencer les écrans de docs/ecrans.md (ex : écran 1.4) quand applicable. -->

### 5.1 [Nom de la fonctionnalité] (écran X.Y — priorité 🔴/🟠/🟡/⚪)

**Description :** …

**Règles métier :**
- RG-1 : …
- RG-2 : …

**Comportement attendu :**
1. …
2. …

**Champs / données concernés :** (tables, colonnes clés)

---

## 6. Critères d'acceptation (Definition of Done)

<!-- Liste de tests fonctionnels que quelqu'un d'autre que le développeur peut vérifier
     à la main ou en test automatisé. -->

| ID   | Critère                                       | Type   |
|------|-----------------------------------------------|--------|
| CA-1 | …                                             | Manuel |
| CA-2 | …                                             | Pytest |

## 7. Contraintes techniques

<!-- Exigences non fonctionnelles propres à ce module. -->

- **Performance :** …
- **Sécurité :** …
- **Multi-tenant :** toutes les requêtes filtrent sur `tenant_id` injecté par la dépendance FastAPI.
- **Audit :** les actions sensibles inscrivent une entrée dans `audit_log`.

## 8. API endpoints (backend)

<!-- Liste des routes FastAPI à implémenter. Format : MÉTHODE /chemin — description courte. -->

| Méthode | Route           | Rôles autorisés         | Description          |
|---------|-----------------|-------------------------|----------------------|
| POST    | `/api/…`        | superviseur             | …                    |

## 9. Modèle de données impacté

<!-- Tables créées ou modifiées. Référencer docs/schema.md pour le DDL complet. -->

- `table_name` : colonnes ajoutées / contraintes nouvelles.

## 10. Dépendances inter-modules

<!-- Autres PRD ou fonctionnalités qui doivent être livrés avant, ou qui consomment ce PRD. -->

- Requiert : PRD-NN (…)
- Requis par : PRD-NN (…)

## 11. Risques & points ouverts

| Risque / Question ouverte           | Probabilité | Impact | Mitigation / décision |
|-------------------------------------|-------------|--------|-----------------------|
| …                                   | Faible      | Moyen  | …                     |

## 12. Jalons

| Jalon                  | Critère de validation            | Date cible |
|------------------------|----------------------------------|------------|
| Migration Alembic OK   | `alembic upgrade head` sans erreur | …        |
| Tests backend verts    | `pytest -q` ≥ 90 % coverage module | …        |
| Écrans P0 navigables   | Démo utilisateur sans bug bloquant | …        |
