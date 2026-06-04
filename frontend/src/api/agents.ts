import { api } from './client';
import type { Agent, AgentCreation, AgentMiseAJour, MonProfilMiseAJour } from './types';

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
