import { NavLink } from 'react-router-dom';
import {
  Home,
  FileText,
  Mail,
  Archive,
  Users,
  Building2,
  AtSign,
  BarChart3,
  ListChecks,
  LayoutGrid,
  Plane,
  Settings,
  Tags,
  type LucideIcon,
} from 'lucide-react';
import type { Role } from '@/api/types';
import { useAuth } from '@/auth/useAuth';
import { ROLE_LABELS } from '@/api/types';
import { cn } from '@/lib/utils';

/**
 * Chaque entrée porte un `accent` qui définit la teinte d'icône / fond
 * quand elle est active ou survolée. Permet de distinguer visuellement
 * les modules sans rajouter de chrome.
 */
type AccentColor = 'brand' | 'docs' | 'courriers' | 'archivage';

interface Entree {
  vers: string;
  libelle: string;
  icone: LucideIcon;
  accent: AccentColor;
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
      { vers: '/accueil',     libelle: 'Accueil',     icone: Home,     accent: 'brand' },
      { vers: '/documents',   libelle: 'Documents',   icone: FileText, accent: 'docs' },
      { vers: '/courriers',   libelle: 'Courriers',   icone: Mail,     accent: 'courriers' },
      { vers: '/redirection', libelle: 'Redirection', icone: Plane,    accent: 'courriers' },
    ],
  },
  {
    titre: 'Référentiels',
    entrees: [
      {
        vers: '/archivage',
        libelle: 'Archivage physique',
        icone: Archive,
        accent: 'archivage',
        roles: ['archiviste', 'superviseur'],
      },
      {
        vers: '/referentiels',
        libelle: 'Catégories / types',
        icone: Tags,
        accent: 'brand',
        roles: ['superviseur'],
      },
      {
        vers: '/departements',
        libelle: 'Départements',
        icone: LayoutGrid,
        accent: 'brand',
        roles: ['superviseur'],
      },
    ],
  },
  {
    titre: 'Administration',
    entrees: [
      { vers: '/agents',          libelle: 'Agents',           icone: Users,      accent: 'brand', roles: ['superviseur'] },
      { vers: '/structure',       libelle: 'Structure',        icone: Building2,  accent: 'brand', roles: ['superviseur'] },
      { vers: '/parametres-mail', libelle: 'Paramètres mail',  icone: AtSign,     accent: 'brand', roles: ['superviseur'] },
      { vers: '/statistiques',    libelle: 'Statistiques',     icone: BarChart3,  accent: 'brand', roles: ['superviseur'] },
      { vers: '/audit-log',       libelle: "Journal d'audit",  icone: ListChecks, accent: 'brand', roles: ['superviseur'] },
    ],
  },
];

/** Classes Tailwind statiques par accent — Tailwind ne peut pas générer
 *  les classes à la volée à partir de variables (purge JIT), donc on les
 *  liste en dur ici. */
const CLASSES_ACCENT: Record<AccentColor, {
  active: string;
  iconActive: string;
  iconHover: string;
  marker: string;
}> = {
  brand: {
    active:     'bg-brand-50 text-brand-800 font-medium',
    iconActive: 'text-brand-700',
    iconHover:  'group-hover:text-brand-600',
    marker:     'bg-brand-700',
  },
  docs: {
    active:     'bg-docs-50 text-docs-800 font-medium',
    iconActive: 'text-docs-600',
    iconHover:  'group-hover:text-docs-600',
    marker:     'bg-docs-600',
  },
  courriers: {
    active:     'bg-courriers-50 text-courriers-800 font-medium',
    iconActive: 'text-courriers-600',
    iconHover:  'group-hover:text-courriers-600',
    marker:     'bg-courriers-600',
  },
  archivage: {
    active:     'bg-archivage-50 text-archivage-800 font-medium',
    iconActive: 'text-archivage-600',
    iconHover:  'group-hover:text-archivage-600',
    marker:     'bg-archivage-600',
  },
};

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
    <aside className="w-64 shrink-0 border-r border-slate-200/80 bg-sidebar-noise flex flex-col">
      {/* Logo / brand — sous-fond très léger marine pour donner du caractère */}
      <div className="relative px-5 py-5 border-b border-slate-100">
        <div
          aria-hidden
          className="absolute inset-0 opacity-50 pointer-events-none"
          style={{
            background:
              'radial-gradient(at 0% 0%, rgba(77,111,156,0.10) 0px, transparent 60%)',
          }}
        />
        <div className="relative flex items-center gap-3">
          <img
            src="/icone_application.png"
            alt="Soft GEDCAP"
            className="h-10 w-10 rounded-xl shadow-card object-contain bg-white ring-1 ring-slate-200/80"
          />
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight leading-none">
              Soft GEDCAP
            </h1>
            <p className="text-[10px] uppercase tracking-wider text-slate-500 mt-1 font-medium">
              GED · GEC · Archivage
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
              {g.entrees.map((e) => {
                const c = CLASSES_ACCENT[e.accent];
                return (
                  <li key={e.vers}>
                    <NavLink
                      to={e.vers}
                      end={e.vers === '/accueil'}
                      className={({ isActive }) =>
                        cn(
                          'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                          isActive
                            ? c.active
                            : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900',
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <span className={cn(
                              'absolute left-0 top-1/2 -translate-y-1/2 h-5 w-1 rounded-r-full',
                              c.marker,
                            )} />
                          )}
                          <e.icone
                            className={cn(
                              'h-4 w-4 shrink-0 transition-colors',
                              isActive
                                ? c.iconActive
                                : ['text-slate-400', c.iconHover].join(' '),
                            )}
                          />
                          <span>{e.libelle}</span>
                        </>
                      )}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Carte utilisateur en bas — gradient marine premium */}
      <div className="border-t border-slate-100 p-3">
        <NavLink
          to="/profil"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors',
              isActive ? 'bg-brand-50' : 'hover:bg-slate-100/80',
            )
          }
        >
          <div className="h-9 w-9 rounded-full bg-gradient-brand shadow-card ring-1 ring-brand-800/20 flex items-center justify-center text-white text-xs font-bold tracking-wide">
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
