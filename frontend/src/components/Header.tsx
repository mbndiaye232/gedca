import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, LogOut, User } from 'lucide-react';
import { useAuth } from '@/auth/useAuth';
import { ROLE_LABELS } from '@/api/types';
import { cn } from '@/lib/utils';

export function Header() {
  const { agent, deconnecter, enChargement } = useAuth();
  const [menuOuvert, setMenuOuvert] = useState(false);

  if (!agent) return null;

  return (
    <header className="h-14 border-b border-gray-200 bg-white flex items-center justify-end px-6">
      <div className="relative">
        <button
          type="button"
          onClick={() => setMenuOuvert((o) => !o)}
          className="flex items-center gap-2 text-sm text-gray-700 hover:text-gray-900"
        >
          <div className="h-8 w-8 rounded-full bg-brand-50 flex items-center justify-center text-brand-700 font-semibold">
            {agent.prenom[0]?.toUpperCase()}{agent.nom[0]?.toUpperCase()}
          </div>
          <div className="text-left hidden sm:block">
            <div className="font-medium">{agent.prenom} {agent.nom}</div>
            <div className="text-xs text-gray-500">{ROLE_LABELS[agent.role]}</div>
          </div>
          <ChevronDown className={cn('h-4 w-4 transition-transform', menuOuvert && 'rotate-180')} />
        </button>

        {menuOuvert && (
          <>
            <div
              className="fixed inset-0 z-10"
              onClick={() => setMenuOuvert(false)}
            />
            <div className="absolute right-0 top-full mt-2 w-56 rounded-lg border border-gray-200 bg-white shadow-lg py-1 z-20">
              <Link
                to="/profil"
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                onClick={() => setMenuOuvert(false)}
              >
                <User className="h-4 w-4" /> Mon profil
              </Link>
              <button
                type="button"
                onClick={() => deconnecter()}
                disabled={enChargement}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <LogOut className="h-4 w-4" /> Déconnexion
              </button>
            </div>
          </>
        )}
      </div>
    </header>
  );
}
