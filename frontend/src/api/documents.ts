import { api, getToken } from './client';
import type { Document, DocumentMetadonnees, DocumentMiseAJour } from './types';

export interface ListerParams {
  q?: string;
  categorie_id?: number;
  statut?: string;
  /** Si true, ne retourne que les documents avec thématique OU type de document manquant. */
  incomplete?: boolean;
  limit?: number;
  offset?: number;
}

export async function listerDocuments(params: ListerParams = {}): Promise<Document[]> {
  const { data } = await api.get<Document[]>('/documents', { params });
  return data;
}

export async function lireDocument(id: number): Promise<Document> {
  const { data } = await api.get<Document>(`/documents/${id}`);
  return data;
}

/**
 * Upload multipart : fichier + métadonnées sérialisées.
 *
 * onProgress est appelé avec un nombre 0..1 pour brancher une barre de progression.
 */
export async function creerDocument(
  fichier: File,
  metadonnees: DocumentMetadonnees,
  onProgress?: (progression: number) => void,
): Promise<Document> {
  const form = new FormData();
  form.append('fichier', fichier);
  form.append('metadonnees', JSON.stringify(metadonnees));

  const { data } = await api.post<Document>('/documents', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(e.loaded / e.total);
    },
  });
  return data;
}

export async function majDocument(id: number, body: DocumentMiseAJour): Promise<Document> {
  const { data } = await api.put<Document>(`/documents/${id}`, body);
  return data;
}

export async function supprimerDocument(id: number): Promise<Document> {
  const { data } = await api.delete<Document>(`/documents/${id}`);
  return data;
}

/**
 * Relance l'extraction de texte (OCR + indexation FTS).
 *
 * Utile pour les documents marqués `ocr_echoue` après un fix
 * d'environnement (Tesseract installé), ou pour rejouer après un
 * changement de stratégie d'extraction.
 */
export async function reextraireDocument(id: number): Promise<Document> {
  const { data } = await api.post<Document>(`/documents/${id}/reextraire`);
  return data;
}

/**
 * Récupère le contenu déchiffré comme Blob.
 *
 * Le Bearer token est injecté automatiquement par l'intercepteur axios.
 * Le caller crée ensuite une `URL.createObjectURL(blob)` pour `<img>`, `<iframe>`
 * ou le passe directement à react-pdf.
 */
export async function telechargerContenu(id: number): Promise<Blob> {
  const response = await api.get<Blob>(`/documents/${id}/contenu`, {
    responseType: 'blob',
  });
  return response.data;
}

/**
 * Construit une URL absolue vers le contenu, utile si on veut court-circuiter
 * axios (réservé aux cas où le token est passé en query param — non utilisé en v1).
 */
export function urlContenuDocument(id: number): string {
  const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';
  return `${base}/documents/${id}/contenu`;
}

export { getToken };
