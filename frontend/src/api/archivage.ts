import { api } from './client';
import type {
  Boite,
  CodeComplet,
  Dossier,
  Local,
  Rayon,
  Site,
  SousDossier,
} from './types';

// ----- Sites ----------------------------------------------------------------

export async function listerSites(): Promise<Site[]> {
  const { data } = await api.get<Site[]>('/archivage/sites');
  return data;
}

export async function creerSite(libelle: string, description?: string): Promise<Site> {
  const { data } = await api.post<Site>('/archivage/sites', { libelle, description });
  return data;
}

export async function majSite(
  id: number,
  body: { libelle?: string; description?: string | null },
): Promise<Site> {
  const { data } = await api.put<Site>(`/archivage/sites/${id}`, body);
  return data;
}

export async function supprimerSite(id: number): Promise<Site> {
  const { data } = await api.delete<Site>(`/archivage/sites/${id}`);
  return data;
}

// ----- Locaux ---------------------------------------------------------------

export async function listerLocaux(siteId: number): Promise<Local[]> {
  const { data } = await api.get<Local[]>(`/archivage/sites/${siteId}/locaux`);
  return data;
}

export async function creerLocal(
  siteId: number,
  libelle: string,
  description?: string,
): Promise<Local> {
  const { data } = await api.post<Local>('/archivage/locaux', {
    site_id: siteId,
    libelle,
    description,
  });
  return data;
}

export async function majLocal(
  id: number,
  body: { libelle?: string; description?: string | null },
): Promise<Local> {
  const { data } = await api.put<Local>(`/archivage/locaux/${id}`, body);
  return data;
}

export async function supprimerLocal(id: number): Promise<Local> {
  const { data } = await api.delete<Local>(`/archivage/locaux/${id}`);
  return data;
}

// ----- Rayons ---------------------------------------------------------------

export async function listerRayons(localId: number): Promise<Rayon[]> {
  const { data } = await api.get<Rayon[]>(`/archivage/locaux/${localId}/rayons`);
  return data;
}

export async function creerRayon(localId: number, libelle: string): Promise<Rayon> {
  const { data } = await api.post<Rayon>('/archivage/rayons', {
    local_id: localId,
    libelle,
  });
  return data;
}

export async function majRayon(id: number, libelle: string): Promise<Rayon> {
  const { data } = await api.put<Rayon>(`/archivage/rayons/${id}`, { libelle });
  return data;
}

export async function supprimerRayon(id: number): Promise<Rayon> {
  const { data } = await api.delete<Rayon>(`/archivage/rayons/${id}`);
  return data;
}

// ----- Boîtes ---------------------------------------------------------------

export async function listerBoites(rayonId: number): Promise<Boite[]> {
  const { data } = await api.get<Boite[]>(`/archivage/rayons/${rayonId}/boites`);
  return data;
}

export async function creerBoite(rayonId: number, libelle: string): Promise<Boite> {
  const { data } = await api.post<Boite>('/archivage/boites', {
    rayon_id: rayonId,
    libelle,
  });
  return data;
}

export async function majBoite(id: number, libelle: string): Promise<Boite> {
  const { data } = await api.put<Boite>(`/archivage/boites/${id}`, { libelle });
  return data;
}

export async function supprimerBoite(id: number): Promise<Boite> {
  const { data } = await api.delete<Boite>(`/archivage/boites/${id}`);
  return data;
}

// ----- Dossiers -------------------------------------------------------------

export async function listerDossiers(boiteId: number): Promise<Dossier[]> {
  const { data } = await api.get<Dossier[]>(`/archivage/boites/${boiteId}/dossiers`);
  return data;
}

export async function creerDossier(boiteId: number, libelle: string): Promise<Dossier> {
  const { data } = await api.post<Dossier>('/archivage/dossiers', {
    boite_id: boiteId,
    libelle,
  });
  return data;
}

export async function majDossier(id: number, libelle: string): Promise<Dossier> {
  const { data } = await api.put<Dossier>(`/archivage/dossiers/${id}`, { libelle });
  return data;
}

export async function supprimerDossier(id: number): Promise<Dossier> {
  const { data } = await api.delete<Dossier>(`/archivage/dossiers/${id}`);
  return data;
}

// ----- Sous-dossiers --------------------------------------------------------

export async function listerSousDossiers(dossierId: number): Promise<SousDossier[]> {
  const { data } = await api.get<SousDossier[]>(
    `/archivage/dossiers/${dossierId}/sous-dossiers`,
  );
  return data;
}

export async function creerSousDossier(
  dossierId: number,
  libelle: string,
): Promise<SousDossier> {
  const { data } = await api.post<SousDossier>('/archivage/sous-dossiers', {
    dossier_id: dossierId,
    libelle,
  });
  return data;
}

export async function majSousDossier(id: number, libelle: string): Promise<SousDossier> {
  const { data } = await api.put<SousDossier>(`/archivage/sous-dossiers/${id}`, {
    libelle,
  });
  return data;
}

export async function supprimerSousDossier(id: number): Promise<SousDossier> {
  const { data } = await api.delete<SousDossier>(`/archivage/sous-dossiers/${id}`);
  return data;
}

// ----- Code complet ---------------------------------------------------------

export async function codeCompletSousDossier(id: number): Promise<CodeComplet> {
  const { data } = await api.get<CodeComplet>(`/archivage/sous-dossiers/${id}/code`);
  return data;
}
