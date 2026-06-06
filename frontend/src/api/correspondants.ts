import { api } from './client';
import type { Correspondant, CorrespondantCreation } from './types';

export interface ListerParams {
  type_id?: number;
  q?: string;
  limit?: number;
}

export async function listerCorrespondants(
  params: ListerParams = {},
): Promise<Correspondant[]> {
  const { data } = await api.get<Correspondant[]>('/correspondants', { params });
  return data;
}

export async function creerCorrespondant(
  body: CorrespondantCreation,
): Promise<Correspondant> {
  const { data } = await api.post<Correspondant>('/correspondants', body);
  return data;
}
