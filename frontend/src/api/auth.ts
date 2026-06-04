import { api } from './client';
import type { ReponseConnexion } from './types';

export async function login(login: string, motDePasse: string): Promise<ReponseConnexion> {
  const { data } = await api.post<ReponseConnexion>('/auth/login', {
    login,
    mot_de_passe: motDePasse,
  });
  return data;
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout');
}
