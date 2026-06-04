import { api } from './client';
import type { Structure, StructureMiseAJour } from './types';

export async function lireStructure(): Promise<Structure> {
  const { data } = await api.get<Structure>('/structure');
  return data;
}

export async function majStructure(body: StructureMiseAJour): Promise<Structure> {
  const { data } = await api.put<Structure>('/structure', body);
  return data;
}
