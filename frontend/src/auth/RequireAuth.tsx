import { Navigate, Outlet, useLocation } from 'react-router-dom';
import type { Role } from '@/api/types';
import { useAuth } from './useAuth';

interface Props {
  /** Si fourni, seuls ces rôles peuvent accéder. */
  roles?: Role[];
}

/**
 * Guard de route :
 * - non connecté → redirige vers /login en mémorisant la destination
 * - connecté mais mauvais rôle → page « Accès refusé »
 */
export function RequireAuth({ roles }: Props) {
  const { agent, estConnecte } = useAuth();
  const location = useLocation();

  if (!estConnecte || !agent) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (roles && !roles.includes(agent.role)) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] p-8">
        <div className="max-w-md text-center">
          <h1 className="text-2xl font-bold text-red-700 mb-2">Accès refusé</h1>
          <p className="text-gray-600">
            Cette page est réservée aux utilisateurs avec un rôle spécifique. Ton
            rôle actuel ne permet pas d'y accéder.
          </p>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
