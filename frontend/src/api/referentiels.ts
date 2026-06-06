import { api } from './client';
import type { Categorie, CategorieCreation, Referentiel } from './types';

// --- Catégories -------------------------------------------------------------

export async function listerCategories(): Promise<Categorie[]> {
  const { data } = await api.get<Categorie[]>('/categories');
  return data;
}

export async function creerCategorie(body: CategorieCreation): Promise<Categorie> {
  const { data } = await api.post<Categorie>('/categories', body);
  return data;
}

export async function majCategorie(
  id: number,
  body: { libelle?: string; description?: string | null },
): Promise<Categorie> {
  const { data } = await api.put<Categorie>(`/categories/${id}`, body);
  return data;
}

export async function supprimerCategorie(id: number): Promise<Categorie> {
  const { data } = await api.delete<Categorie>(`/categories/${id}`);
  return data;
}

// --- Thématiques ------------------------------------------------------------

export async function listerThematiques(): Promise<Referentiel[]> {
  const { data } = await api.get<Referentiel[]>('/thematiques');
  return data;
}

export async function creerThematique(libelle: string): Promise<Referentiel> {
  const { data } = await api.post<Referentiel>('/thematiques', { libelle });
  return data;
}

export async function majThematique(id: number, libelle: string): Promise<Referentiel> {
  const { data } = await api.put<Referentiel>(`/thematiques/${id}`, { libelle });
  return data;
}

export async function supprimerThematique(id: number): Promise<Referentiel> {
  const { data } = await api.delete<Referentiel>(`/thematiques/${id}`);
  return data;
}

// --- Types de document ------------------------------------------------------

export async function listerTypesDocument(): Promise<Referentiel[]> {
  const { data } = await api.get<Referentiel[]>('/types-document');
  return data;
}

export async function creerTypeDocument(libelle: string): Promise<Referentiel> {
  const { data } = await api.post<Referentiel>('/types-document', { libelle });
  return data;
}

export async function majTypeDocument(id: number, libelle: string): Promise<Referentiel> {
  const { data } = await api.put<Referentiel>(`/types-document/${id}`, { libelle });
  return data;
}

export async function supprimerTypeDocument(id: number): Promise<Referentiel> {
  const { data } = await api.delete<Referentiel>(`/types-document/${id}`);
  return data;
}
