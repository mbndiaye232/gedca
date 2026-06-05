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

// --- Thématiques ------------------------------------------------------------

export async function listerThematiques(): Promise<Referentiel[]> {
  const { data } = await api.get<Referentiel[]>('/thematiques');
  return data;
}

export async function creerThematique(libelle: string): Promise<Referentiel> {
  const { data } = await api.post<Referentiel>('/thematiques', { libelle });
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
