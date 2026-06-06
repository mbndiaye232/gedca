import { NavLink } from 'react-router-dom';
import {
  Home,
  FileText,
  Mail,
  Archive,
  Users,
  Building2,
  AtSign,
  ListChecks,
  LayoutGrid,
  Settings,
  Tags,
  type LucideIcon,
} from 'lucide-react';
import type { Role } from '@/api/types';
import { useAuth } from '@/auth/useAuth';
import { ROLE_LABELS } from '@/api/types';
import { cn } from '@/lib/utils';

interface Entree {
  vers: string;
  libelle: string;
  icone: LucideIcon;
  roles?: Role[];
}

interface Groupe {
  titre: string;
  entrees: Entree[];
}

const GROUPES: Groupe[] = [
  {
    titre: 'Espace de travail',
    entrees: [
      { vers: '/accueil', libelle: 'Accueil', icone: Home },
      { vers: '/documents', libelle: 'Documents', icone: FileText },
      { vers: '/courriers', libelle: 'Courriers', icone: Mail },
    ],
  },
  {
    titre: 'Référentiels',
    entrees: [
      {
        vers: '/archivage',
        libelle: 'Archivage physique',
        icone: Archive,
        roles: ['archiviste', 'superviseur'],
      },
      { vers: '/referentiels', libelle: 'Catégories / types', icone: Tags, roles: ['superviseur'] },
      { vers: '/departements', libelle: 'Départements', icone: LayoutGrid, roles: ['superviseur'] },
    ],
  },
  {
    titre: 'Administration',
    entrees: [
      { vers: '/agents', libelle: 'Agents', icone: Users, roles: ['superviseur'] },
      { vers: '/structure', libelle: 'Structure', icone: Building2, roles: ['superviseur'] },
      { vers: '/parametres-mail', libelle: 'Paramètres mail', icone: AtSign, roles: ['superviseur'] },
      { vers: '/audit-log', libelle: 'Journal d\'audit', icone: ListChecks, roles: ['superviseur'] },
    ],
  },
];

export function Sidebar() {
  const { agent } = useAuth();
  if (!agent) return null;

  const groupesVisibles = GROUPES
    .map((g) => ({
      ...g,
      entrees: g.entrees.filter((e) => !e.roles || e.roles.includes(agent.role)),
    }))
    .filter((g) => g.entrees.length > 0);

  return (
    <aside className="w-64 shrink-0 border-r border-slate-200 bg-white flex flex-col">
      {/* Logo / brand */}
      <div className="px-5 py-5 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-brand shadow-sm flex items-center justify-center text-white font-bold tracking-tight">
            G
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight leading-none">
              GEDCA
            </h1>
            <p className="text-[10px] uppercase tracking-wider text-slate-400 mt-1">
              Gestion documentaire
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {groupesVisibles.map((g) => (
          <div key={g.titre}>
            <h2 className="px-3 mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {g.titre}
            </h2>
            <ul className="space-y-0.5">
              {g.entrees.map((e) => (
                <li key={e.vers}>
                  <NavLink
                    to={e.vers}
                    end={e.vers === '/accueil'}
                    className={({ isActive }) =>
                      cn(
                        'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                        isActive
                          ? 'bg-brand-50 text-brand-700 font-medium'
                          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900',
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-1 rounded-r-full bg-brand-600" />
                        )}
                        <e.icone
                          className={cn(
                            'h-4 w-4 shrink-0',
                            isActive ? 'text-brand-600' : 'text-slate-400 group-hover:text-slate-600',
                          )}
                        />
                        <span>{e.libelle}</span>
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* Carte utilisateur en bas */}
      <div className="border-t border-slate-100 p-3">
        <NavLink
          to="/profil"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors',
              isActive ? 'bg-slate-100' : 'hover:bg-slate-50',
            )
          }
        >
          <div className="h-9 w-9 rounded-full bg-gradient-brand shadow-sm flex items-center justify-center text-white text-xs font-bold">
            {agent.prenom[0]?.toUpperCase()}
            {agent.nom[0]?.toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-slate-900 truncate">
              {agent.prenom} {agent.nom}
            </p>
            <p className="text-xs text-slate-500 truncate">{ROLE_LABELS[agent.role]}</p>
          </div>
          <Settings className="h-4 w-4 text-slate-400 shrink-0" />
        </NavLink>
      </div>
    </aside>
  );
}
