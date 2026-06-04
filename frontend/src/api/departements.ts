import { api } from './client';
import type { Departement, DepartementCreation, DepartementMiseAJour } from './types';

export async function listerDepartements(): Promise<Departement[]> {
  const { data } = await api.get<Departement[]>('/departements');
  return data;
}

export async function creerDepartement(body: DepartementCreation): Promise<Departement> {
  const { data } = await api.post<Departement>('/departements', body);
  return data;
}

export async function majDepartement(id: number, body: DepartementMiseAJour): Promise<Departement> {
  const { data } = await api.put<Departement>(`/departements/${id}`, body);
  return data;
}

export async function desactiverDepartement(id: number): Promise<Departement> {
  const { data } = await api.delete<Departement>(`/departements/${id}`);
  return data;
}
