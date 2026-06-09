import { api } from './client';
import type { RedirectionCreation, RedirectionDetail } from './types';

/**
 * Récupère ma redirection active (ou null si je n'en ai pas).
 *
 * Endpoint accessible à tout agent connecté.
 */
export async function maRedirection(): Promise<RedirectionDetail | null> {
  const { data } = await api.get<RedirectionDetail | null>('/redirections/me');
  return data;
}

/** Crée ma redirection vers le substitut choisi (PDF redirection p. 1). */
export async function creerRedirection(
  body: RedirectionCreation,
): Promise<RedirectionDetail> {
  const { data } = await api.post<RedirectionDetail>('/redirections', body);
  return data;
}

/** Supprime (désactive) une redirection. */
export async function supprimerRedirection(
  id: number,
): Promise<RedirectionDetail> {
  const { data } = await api.delete<RedirectionDetail>(`/redirections/${id}`);
  return data;
}

/** Liste de toutes les redirections actives — vue superviseur. */
export async function listerRedirections(): Promise<RedirectionDetail[]> {
  const { data } = await api.get<RedirectionDetail[]>('/redirections');
  return data;
}
