import { api } from './client';

export interface ParametresSmtpLecture {
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_user: string | null;
  smtp_from: string | null;
  smtp_use_tls: boolean;
  password_defini: boolean;
}

export interface ParametresSmtpMiseAJour {
  smtp_host?: string | null;
  smtp_port?: number | null;
  smtp_user?: string | null;
  /**
   * Sémantique :
   * - `undefined` ou omis → conserver le mot de passe existant
   * - `""` chaîne vide → effacer le mot de passe
   * - autre → définir le nouveau (sera chiffré côté backend)
   */
  smtp_password?: string | null;
  smtp_from?: string | null;
  smtp_use_tls?: boolean;
}

export interface ResultatTestSmtp {
  envoye: boolean;
  destinataire: string;
  erreur: string | null;
}

export async function lireParametresSmtp(): Promise<ParametresSmtpLecture> {
  const { data } = await api.get<ParametresSmtpLecture>('/parametres-smtp/me');
  return data;
}

export async function majParametresSmtp(
  body: ParametresSmtpMiseAJour,
): Promise<ParametresSmtpLecture> {
  const { data } = await api.put<ParametresSmtpLecture>(
    '/parametres-smtp/me',
    body,
  );
  return data;
}

export async function testerSmtp(
  destinataire?: string,
): Promise<ResultatTestSmtp> {
  const { data } = await api.post<ResultatTestSmtp>(
    '/parametres-smtp/me/tester',
    { destinataire: destinataire || null },
  );
  return data;
}
