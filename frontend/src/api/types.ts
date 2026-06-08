/**
 * Types des entités exposées par l'API.
 * Doivent rester alignés avec les schémas Pydantic backend.
 */

export type Role = 'superviseur' | 'archiviste' | 'agent_standard';

export interface AgentSession {
  id: number;
  login: string;
  nom: string;
  prenom: string;
  email: string | null;
  role: Role;
  tenant_id: number;
}

export interface ReponseConnexion {
  access_token: string;
  token_type: 'bearer';
  expire_at: string; // ISO datetime
  agent: AgentSession;
}

export interface Agent {
  id: number;
  login: string;
  nom: string;
  prenom: string;
  email: string | null;
  telephone: string | null;
  cellulaire: string | null;
  adresse: string | null;
  fonction: string | null;
  photo_chemin: string | null;
  departement_id: number | null;
  role_id: number;
  actif: boolean;
  derniere_connexion: string | null;
  created_at: string;
}

export interface AgentCreation {
  login: string;
  mot_de_passe: string;
  nom: string;
  prenom: string;
  email?: string | null;
  telephone?: string | null;
  cellulaire?: string | null;
  adresse?: string | null;
  fonction?: string | null;
  departement_id?: number | null;
  role_id: number;
}

export interface AgentMiseAJour {
  nom?: string;
  prenom?: string;
  email?: string | null;
  telephone?: string | null;
  cellulaire?: string | null;
  adresse?: string | null;
  fonction?: string | null;
  departement_id?: number | null;
  role_id?: number;
}

export interface MonProfilMiseAJour {
  email?: string | null;
  telephone?: string | null;
  cellulaire?: string | null;
  adresse?: string | null;
  photo_chemin?: string | null;
  mot_de_passe_actuel?: string;
  nouveau_mot_de_passe?: string;
}

export interface Departement {
  id: number;
  code: string | null;
  libelle: string;
  actif: boolean;
  created_at: string;
}

export interface DepartementCreation {
  code?: string | null;
  libelle: string;
}

export interface DepartementMiseAJour {
  code?: string | null;
  libelle?: string;
}

export interface Structure {
  id: number;
  code: string;
  raison_sociale: string;
  adresse: string | null;
  telephone: string | null;
  email: string | null;
  logo_chemin: string | null;
}

export interface StructureMiseAJour {
  raison_sociale?: string;
  adresse?: string | null;
  telephone?: string | null;
  email?: string | null;
  logo_chemin?: string | null;
}

export interface AuditLogEntry {
  id: number;
  agent_id: number | null;
  action: string;
  entite: string | null;
  entite_id: number | null;
  payload: Record<string, unknown>;
  ip: string | null;
  user_agent: string | null;
  ts: string;
}

export interface PageAuditLog {
  items: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiError {
  detail: string;
}

// ---------------------------------------------------------------------------
// PRD-02 — Documents et référentiels
// ---------------------------------------------------------------------------

export interface EmplacementResume {
  sous_dossier_id: number;
  code_complet: string;
  site: NiveauResume;
  local: NiveauResume;
  rayon: NiveauResume;
  boite: NiveauResume;
  dossier: NiveauResume;
  sous_dossier: NiveauResume;
}

export interface Document {
  id: number;
  titre: string;
  description: string | null;
  resume: string | null;
  mots_cles: string | null;
  categorie_id: number | null;
  thematique_id: number | null;
  type_document_id: number | null;
  mime: string;
  taille_octets: number;
  checksum_sha256: string;
  date_document: string | null;
  date_numerisation: string | null;
  confidentiel: boolean;
  origine: string;
  statut: string;
  metadata: Record<string, unknown>;
  emplacement: EmplacementResume | null;
  created_at: string;
  created_by: number | null;
  updated_at: string;
}

export interface DocumentMetadonnees {
  titre: string;
  description?: string | null;
  resume?: string | null;
  mots_cles?: string | null;
  categorie_id: number;
  thematique_id?: number | null;
  type_document_id?: number | null;
  date_document?: string | null;
  confidentiel?: boolean;
  sous_dossier_id?: number | null;
}

export interface DocumentMiseAJour {
  titre?: string;
  description?: string | null;
  resume?: string | null;
  mots_cles?: string | null;
  categorie_id?: number | null;
  thematique_id?: number | null;
  type_document_id?: number | null;
  date_document?: string | null;
  confidentiel?: boolean;
  /**
   * Lien physique vers un sous-dossier. Présent dans le JSON et `null` retire
   * le lien existant ; champ omis = pas de modification.
   */
  sous_dossier_id?: number | null;
}

export interface Categorie {
  id: number;
  libelle: string;
  description: string | null;
  actif: boolean;
}

export interface CategorieCreation {
  libelle: string;
  description?: string | null;
}

export interface Referentiel {
  id: number;
  libelle: string;
  actif: boolean;
}

// ---------------------------------------------------------------------------
// PRD-05 — Archivage physique
// ---------------------------------------------------------------------------

interface _EmplacementBase {
  id: number;
  numero: number;
  libelle: string;
}

export interface Site extends _EmplacementBase {
  description: string | null;
}

export interface Local extends _EmplacementBase {
  site_id: number;
  description: string | null;
}

export interface Rayon extends _EmplacementBase {
  local_id: number;
}

export interface Boite extends _EmplacementBase {
  rayon_id: number;
}

export interface Dossier extends _EmplacementBase {
  boite_id: number;
}

export interface SousDossier extends _EmplacementBase {
  dossier_id: number;
}

export interface NiveauResume {
  numero: number;
  libelle: string;
}

export interface CodeComplet {
  sous_dossier_id: number;
  code_complet: string; // ex: "05.02.01.001.04.07"
  site: NiveauResume;
  local: NiveauResume;
  rayon: NiveauResume;
  boite: NiveauResume;
  dossier: NiveauResume;
  sous_dossier: NiveauResume;
}

/** Mapping rôle code ↔ role_id côté DB (cohérent avec migration 001). */
export const ROLE_IDS: Record<Role, number> = {
  superviseur: 1,
  archiviste: 2,
  agent_standard: 3,
};

export const ROLE_LABELS: Record<Role, string> = {
  superviseur: 'Superviseur',
  archiviste: 'Archiviste',
  agent_standard: 'Agent',
};

export function roleFromId(roleId: number): Role {
  return (Object.entries(ROLE_IDS).find(([, id]) => id === roleId)?.[0] ?? 'agent_standard') as Role;
}

// ---------------------------------------------------------------------------
// Correspondants
// ---------------------------------------------------------------------------

export interface Correspondant {
  id: number;
  type_id: number;
  raison_sociale: string | null;
  civilite: string | null;
  nom: string | null;
  prenom: string | null;
  fonction: string | null;
  adresse: string | null;
  telephone: string | null;
  email: string | null;
  actif: boolean;
}

export interface CorrespondantCreation {
  type_id: number;
  raison_sociale?: string | null;
  civilite?: string | null;
  nom?: string | null;
  prenom?: string | null;
  fonction?: string | null;
  adresse?: string | null;
  telephone?: string | null;
  email?: string | null;
}

// ---------------------------------------------------------------------------
// PRD-06A — Courriers
// ---------------------------------------------------------------------------

export type SensCourrier = 'entrant' | 'sortant' | 'interne';

export type CorbeilleCode =
  | 'a_traiter'
  | 'traite'
  | 'en_copie'
  | 'en_retard'
  | 'a_valider'
  | 'valides'
  | 'a_faire_valider'
  | 'en_validation';

export interface CompteurCorbeille {
  code: CorbeilleCode;
  libelle: string;
  compteur: number;
  actif_en_06a: boolean;
}

export interface CompteursCorbeilles {
  corbeilles: CompteurCorbeille[];
}

export interface StatutCourrierLecture {
  id: number;
  code: string;
  libelle: string;
}

export interface ActionCourrierLecture {
  id: number;
  code: string;
  libelle: string;
}

export interface AgentResume {
  id: number;
  nom: string;
  prenom: string;
  email: string | null;
}

export interface CorrespondantResume {
  id: number;
  raison_sociale: string | null;
  nom: string | null;
  prenom: string | null;
}

export interface NoteCourrier {
  id: number;
  agent_id: number | null;
  contenu: string;
  created_at: string;
}

export interface HistoriqueCourrier {
  id: number;
  agent_id: number | null;
  action: ActionCourrierLecture;
  payload: Record<string, unknown>;
  ts: string;
}

export interface Courrier {
  id: number;
  numero_enregistrement: string;
  sens: SensCourrier;
  ref_externe: string | null;
  categorie_id: number | null;
  objet: string;
  mots_cles: string | null;
  observations: string | null;
  date_courrier: string | null;
  date_arrivee: string | null;
  date_limite: string | null;
  correspondant_id: number | null;
  correspondant: CorrespondantResume | null;
  agent_destinataire_id: number;
  agent_proprietaire_id: number;
  departement_destinataire_id: number | null;
  document_principal_id: number;
  statut: StatutCourrierLecture;
  courrier_origine_id: number | null;
  created_at: string;
  created_by: number | null;
  updated_at: string;
}

export interface CourrierDetail extends Courrier {
  copies: AgentResume[];
  notes: NoteCourrier[];
  historique: HistoriqueCourrier[];
  pieces_additionnelles: number[];
}

export interface CourrierCreationBody {
  sens: SensCourrier;
  ref_externe?: string | null;
  categorie_id?: number | null;
  objet: string;
  mots_cles?: string | null;
  observations?: string | null;
  date_courrier?: string | null;
  date_arrivee?: string | null;
  date_limite?: string | null;
  correspondant_id?: number | null;
  departement_destinataire_id?: number | null;
  agent_destinataire_id: number;
  document_titre: string;
  document_categorie_id: number;
}

export interface RepondreBody {
  objet: string;
  mots_cles?: string | null;
  observations?: string | null;
  date_limite?: string | null;
  correspondant_id?: number | null;
  // Optionnel : si non fourni, le backend remonte la réponse à l'agent
  // qui m'a imputé le courrier (ou me la laisse si je suis le proprio
  // d'origine).
  agent_destinataire_id?: number | null;
  departement_destinataire_id?: number | null;
  document_titre: string;
  document_categorie_id: number;
}
