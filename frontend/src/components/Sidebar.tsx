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
  type LucideIcon,
} from 'lucide-react';
import type { Role } from '@/api/types';
import { useAuth } from '@/auth/useAuth';
import { cn } from '@/lib/utils';

interface Entree {
  vers: string;
  libelle: string;
  icone: LucideIcon;
  /** Si fourni, seuls ces rôles voient l'entrée. */
  roles?: Role[];
}

const ENTREES: Entree[] = [
  { vers: '/accueil', libelle: 'Accueil', icone: Home },
  { vers: '/documents', libelle: 'Documents', icone: FileText }, // PRD-02
  { vers: '/courriers', libelle: 'Courriers', icone: Mail }, // PRD-06
  { vers: '/archivage', libelle: 'Archivage', icone: Archive, roles: ['archiviste', 'superviseur'] },
  { vers: '/agents', libelle: 'Agents', icone: Users, roles: ['superviseur'] },
  { vers: '/departements', libelle: 'Départements', icone: Building2, roles: ['superviseur'] },
  { vers: '/structure', libelle: 'Structure', icone: Building2, roles: ['superviseur'] },
  { vers: '/parametres-mail', libelle: 'Paramètres mail', icone: AtSign, roles: ['superviseur'] },
  { vers: '/audit-log', libelle: 'Journal d\'audit', icone: ListChecks, roles: ['superviseur'] },
];

export function Sidebar() {
  const { agent } = useAuth();
  if (!agent) return null;

  const entreesVisibles = ENTREES.filter(
    (e) => !e.roles || e.roles.includes(agent.role),
  );

  return (
    <nav className="w-60 shrink-0 border-r border-gray-200 bg-white">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-xl font-bold text-brand-700">GEDCA</h1>
        <p className="text-xs text-gray-500 mt-0.5">Gestion documentaire</p>
      </div>
      <ul className="p-2 space-y-1">
        {entreesVisibles.map((e) => (
          <li key={e.vers}>
            <NavLink
              to={e.vers}
              end={e.vers === '/accueil'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm',
                  isActive
                    ? 'bg-brand-50 text-brand-700 font-medium'
                    : 'text-gray-700 hover:bg-gray-100',
                )
              }
            >
              <e.icone className="h-4 w-4" />
              <span>{e.libelle}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
