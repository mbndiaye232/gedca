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
