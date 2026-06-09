import { api } from './client';
import type {
  CompteursCorbeilles,
  CorbeilleCode,
  Courrier,
  CourrierCreationBody,
  CourrierDetail,
  DemanderValidationBody,
  NoteCourrier,
  RepondreBody,
} from './types';

// --- Corbeilles -------------------------------------------------------------

export async function compteursCorbeilles(): Promise<CompteursCorbeilles> {
  const { data } = await api.get<CompteursCorbeilles>('/courriers/corbeilles/compteurs');
  return data;
}

export async function listerCourriers(
  corbeille: CorbeilleCode,
  limit = 50,
  offset = 0,
): Promise<Courrier[]> {
  const { data } = await api.get<Courrier[]>('/courriers', {
    params: { corbeille, limit, offset },
  });
  return data;
}

// --- Détail -----------------------------------------------------------------

export async function lireCourrier(id: number): Promise<CourrierDetail> {
  const { data } = await api.get<CourrierDetail>(`/courriers/${id}`);
  return data;
}

// --- Création (multipart : pièce principale + JSON métadonnées) -------------

export async function creerCourrier(
  fichier: File,
  body: CourrierCreationBody,
  onProgress?: (p: number) => void,
): Promise<Courrier> {
  const form = new FormData();
  form.append('fichier', fichier);
  form.append('metadonnees', JSON.stringify(body));
  const { data } = await api.post<Courrier>('/courriers', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(e.loaded / e.total);
    },
  });
  return data;
}

// --- Actions ---------------------------------------------------------------

export async function faireUneCopie(
  id: number,
  agentIds: number[],
): Promise<CourrierDetail> {
  const { data } = await api.post<CourrierDetail>(`/courriers/${id}/copies`, {
    agent_ids: agentIds,
  });
  return data;
}

export async function imputer(
  id: number,
  agentImputeId: number,
  instruction?: string,
): Promise<CourrierDetail> {
  const { data } = await api.post<CourrierDetail>(`/courriers/${id}/imputer`, {
    agent_impute_id: agentImputeId,
    instruction: instruction || null,
  });
  return data;
}

export async function envoyer(id: number): Promise<Courrier> {
  const { data } = await api.post<Courrier>(`/courriers/${id}/envoyer`);
  return data;
}

export async function ajouterNote(id: number, contenu: string): Promise<NoteCourrier> {
  const { data } = await api.post<NoteCourrier>(`/courriers/${id}/notes`, { contenu });
  return data;
}

export async function ajouterPiece(
  id: number,
  fichier: File,
  titre: string,
  categorieId: number,
): Promise<CourrierDetail> {
  const form = new FormData();
  form.append('fichier', fichier);
  form.append('titre', titre);
  form.append('categorie_id', String(categorieId));
  const { data } = await api.post<CourrierDetail>(`/courriers/${id}/documents`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function repondre(
  id: number,
  fichier: File,
  body: RepondreBody,
): Promise<Courrier> {
  const form = new FormData();
  form.append('fichier', fichier);
  form.append('metadonnees', JSON.stringify(body));
  const { data } = await api.post<Courrier>(`/courriers/${id}/repondre`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function supprimerCourrier(id: number): Promise<Courrier> {
  const { data } = await api.delete<Courrier>(`/courriers/${id}`);
  return data;
}

// --- Workflow validation (PRD-06B) -----------------------------------------

/**
 * Transmet le courrier à l'agent valideur choisi.
 * Préconditions côté backend : je suis propriétaire ET statut=a_faire_valider.
 * Effet : statut → en_validation, le courrier sort de ma corbeille
 * « À faire valider » et entre dans « En validation » (côté moi) et
 * « À valider » (côté valideur).
 */
export async function demanderValidation(
  id: number,
  body: DemanderValidationBody,
): Promise<Courrier> {
  const { data } = await api.post<Courrier>(
    `/courriers/${id}/demander-validation`,
    body,
  );
  return data;
}

/**
 * Valide un courrier qu'on a reçu en demande de validation.
 * Préconditions côté backend : je suis l'agent_valideur_id ET statut=en_validation.
 * Effet : statut → valide, le courrier sort de ma corbeille « À valider »
 * et apparaît dans la corbeille « Validés » du demandeur.
 */
export async function validerCourrier(id: number): Promise<Courrier> {
  const { data } = await api.post<Courrier>(`/courriers/${id}/valider`);
  return data;
}
