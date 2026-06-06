import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
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
  const queryClient = useQueryClient();
  const [agent, setAgent] = useState<AgentSession | null>(() => getStoredAgent<AgentSession>());
  const [enChargement, setEnChargement] = useState(false);

  // Si le token est absent au chargement initial, l'agent doit être null
  useEffect(() => {
    if (!getToken()) {
      setAgent(null);
    }
  }, []);

  const connecter = useCallback(
    async (login: string, motDePasse: string) => {
      setEnChargement(true);
      try {
        const reponse = await authApi.login(login, motDePasse);
        setToken(reponse.access_token);
        setStoredAgent(reponse.agent);
        setAgent(reponse.agent);
        // CRITIQUE : purger le cache React Query — sinon les données du
        // précédent utilisateur restent visibles tant qu'elles ne sont pas
        // explicitement réinvalidées (fuite cross-session).
        queryClient.clear();
      } finally {
        setEnChargement(false);
      }
    },
    [queryClient],
  );

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
      // Purge cache au logout pour ne rien laisser fuiter à la prochaine session.
      queryClient.clear();
      setEnChargement(false);
    }
  }, [queryClient]);

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
