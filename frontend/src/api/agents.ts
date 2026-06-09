import { api } from './client';
import type {
  Agent,
  AgentCreation,
  AgentDestinataire,
  AgentMiseAJour,
  MonProfilMiseAJour,
} from './types';

export async function lireMonProfil(): Promise<Agent> {
  const { data } = await api.get<Agent>('/agents/me');
  return data;
}

export async function majMonProfil(body: MonProfilMiseAJour): Promise<Agent> {
  const { data } = await api.put<Agent>('/agents/me', body);
  return data;
}

export async function listerAgents(): Promise<Agent[]> {
  const { data } = await api.get<Agent[]>('/agents');
  return data;
}

/**
 * Annuaire des agents actifs accessible à tout agent connecté.
 *
 * À utiliser dans les sélecteurs (imputation, mise en copie, choix d'un
 * destinataire de courrier, choix d'un valideur PRD-06B). Le `listerAgents`
 * ci-dessus reste réservé à la page d'administration RH (superviseur
 * uniquement) et renvoie 403 aux autres rôles.
 */
export async function listerAgentsDestinataires(): Promise<AgentDestinataire[]> {
  const { data } = await api.get<AgentDestinataire[]>('/agents/destinataires');
  return data;
}

export async function creerAgent(body: AgentCreation): Promise<Agent> {
  const { data } = await api.post<Agent>('/agents', body);
  return data;
}

export async function lireAgent(id: number): Promise<Agent> {
  const { data } = await api.get<Agent>(`/agents/${id}`);
  return data;
}

export async function majAgent(id: number, body: AgentMiseAJour): Promise<Agent> {
  const { data } = await api.put<Agent>(`/agents/${id}`, body);
  return data;
}

export async function desactiverAgent(id: number): Promise<Agent> {
  const { data } = await api.post<Agent>(`/agents/${id}/desactiver`);
  return data;
}

/**
 * Initie la réinitialisation de mot de passe d'un agent (superviseur).
 *
 * Le backend génère un token aléatoire de 24h, l'envoie par email à
 * l'agent qui suivra le lien `/reset-mdp?token=...` pour saisir son
 * nouveau mot de passe.
 */
export async function initierResetMdpAgent(id: number): Promise<{
  email_envoye: boolean;
  destinataire_email: string | null;
  duree_validite_heures: number;
}> {
  const { data } = await api.post(`/agents/${id}/reset-mdp/initier`);
  return data;
}
