import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bell, ChevronDown, LogOut, Search, User as UserIcon } from 'lucide-react';
import { useAuth } from '@/auth/useAuth';
import { ROLE_LABELS } from '@/api/types';
import { cn } from '@/lib/utils';

const LIBELLES: Record<string, string> = {
  accueil: 'Accueil',
  documents: 'Documents',
  nouveau: 'Nouveau',
  courriers: 'Courriers',
  archivage: 'Archivage physique',
  agents: 'Agents',
  departements: 'Départements',
  structure: 'Structure',
  'parametres-mail': 'Paramètres mail',
  'audit-log': 'Journal d\'audit',
  profil: 'Mon profil',
};

function libelliser(segment: string): string {
  return LIBELLES[segment] ?? segment;
}

export function Header() {
  const { agent, deconnecter, enChargement } = useAuth();
  const location = useLocation();
  const [menuOuvert, setMenuOuvert] = useState(false);

  if (!agent) return null;

  const segments = location.pathname.split('/').filter(Boolean);

  return (
    <header className="h-16 border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-30">
      <div className="h-full flex items-center justify-between px-6">
        {/* Breadcrumb */}
        <nav aria-label="fil d'Ariane" className="flex items-center gap-1.5 text-sm">
          {segments.length === 0 ? (
            <span className="text-slate-500">Tableau de bord</span>
          ) : (
            segments.map((s, i) => {
              const path = '/' + segments.slice(0, i + 1).join('/');
              const dernier = i === segments.length - 1;
              return (
                <span key={path} className="flex items-center gap-1.5">
                  {i > 0 && <span className="text-slate-300">/</span>}
                  {dernier ? (
                    <span className="font-medium text-slate-900">{libelliser(s)}</span>
                  ) : (
                    <Link to={path} className="text-slate-500 hover:text-slate-900 transition-colors">
                      {libelliser(s)}
                    </Link>
                  )}
                </span>
              );
            })
          )}
        </nav>

        {/* Recherche + actions + menu */}
        <div className="flex items-center gap-3">
          {/* Recherche globale (placeholder pour l'instant) */}
          <div className="hidden md:flex items-center gap-2 h-9 px-3 rounded-lg border border-slate-200 bg-slate-50 text-slate-400 text-sm w-72 cursor-not-allowed">
            <Search className="h-4 w-4" />
            <span className="flex-1">Rechercher…</span>
            <kbd className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-mono text-slate-500">
              ⌘K
            </kbd>
          </div>

          {/* Notifications (placeholder) */}
          <button
            type="button"
            className="relative p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
            title="Notifications"
          >
            <Bell className="h-4 w-4" />
          </button>

          {/* Menu utilisateur */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setMenuOuvert((o) => !o)}
              className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <div className="h-7 w-7 rounded-full bg-gradient-brand shadow-sm flex items-center justify-center text-white text-[10px] font-bold">
                {agent.prenom[0]?.toUpperCase()}
                {agent.nom[0]?.toUpperCase()}
              </div>
              <ChevronDown
                className={cn(
                  'h-3.5 w-3.5 text-slate-400 transition-transform',
                  menuOuvert && 'rotate-180',
                )}
              />
            </button>

            {menuOuvert && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOuvert(false)} />
                <div className="absolute right-0 top-full mt-2 w-64 rounded-xl border border-slate-200 bg-white shadow-elevated py-1 z-20 animate-fade-in">
                  <div className="px-4 py-3 border-b border-slate-100">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {agent.prenom} {agent.nom}
                    </p>
                    <p className="text-xs text-slate-500 truncate">{agent.email}</p>
                    <p className="mt-1 text-xs text-slate-400">{ROLE_LABELS[agent.role]}</p>
                  </div>
                  <Link
                    to="/profil"
                    className="flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                    onClick={() => setMenuOuvert(false)}
                  >
                    <UserIcon className="h-4 w-4 text-slate-400" /> Mon profil
                  </Link>
                  <button
                    type="button"
                    onClick={() => deconnecter()}
                    disabled={enChargement}
                    className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                  >
                    <LogOut className="h-4 w-4 text-slate-400" /> Déconnexion
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
