import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  clearToken,
  getStoredAgent,
  getToken,
  setStoredAgent,
  setToken,
} from '@/api/client';
import * as authApi from '@/api/auth';
import type { AgentSession } from '@/api/types';

interface AuthContextValue {
  agent: AgentSession | null;
  estConnecte: boolean;
  enChargement: boolean;
  connecter: (login: string, motDePasse: string) => Promise<void>;
  deconnecter: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [agent, setAgent] = useState<AgentSession | null>(() => getStoredAgent<AgentSession>());
  const [enChargement, setEnChargement] = useState(false);

  // Si le token est absent au chargement initial, l'agent doit être null
  useEffect(() => {
    if (!getToken()) {
      setAgent(null);
    }
  }, []);

  const connecter = useCallback(async (login: string, motDePasse: string) => {
    setEnChargement(true);
    try {
      const reponse = await authApi.login(login, motDePasse);
      setToken(reponse.access_token);
      setStoredAgent(reponse.agent);
      setAgent(reponse.agent);
    } finally {
      setEnChargement(false);
    }
  }, []);

  const deconnecter = useCallback(async () => {
    setEnChargement(true);
    try {
      try {
        await authApi.logout();
      } catch {
        // En cas d'erreur réseau on déconnecte quand même côté client
      }
    } finally {
      clearToken();
      setAgent(null);
      setEnChargement(false);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      agent,
      estConnecte: agent !== null,
      enChargement,
      connecter,
      deconnecter,
    }),
    [agent, enChargement, connecter, deconnecter],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
