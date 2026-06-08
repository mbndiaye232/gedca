import { type ReactNode } from 'react';
import { type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

type Accent = 'brand' | 'docs' | 'courriers' | 'archivage';

interface Props {
  titre: string;
  sousTitre?: string;
  /** Élément(s) alignés à droite (boutons d'action). */
  actions?: ReactNode;
  /** Pour ajouter un breadcrumb ou un fil au-dessus du titre. */
  fil?: ReactNode;
  /** Couleur thématique du module — pose un badge devant le titre. */
  accent?: Accent;
  /** Icône du module (Lucide). Affichée dans le badge si `accent` est défini. */
  icone?: LucideIcon;
  /** Texte du badge (par défaut : le nom du module dérivé de `accent`). */
  module?: string;
  className?: string;
}

const ACCENT_BADGE: Record<Accent, string> = {
  brand:      'bg-brand-50 text-brand-800 ring-1 ring-inset ring-brand-100',
  docs:       'bg-docs-50 text-docs-800 ring-1 ring-inset ring-docs-100',
  courriers:  'bg-courriers-50 text-courriers-800 ring-1 ring-inset ring-courriers-100',
  archivage:  'bg-archivage-50 text-archivage-800 ring-1 ring-inset ring-archivage-100',
};

const ACCENT_ICON: Record<Accent, string> = {
  brand:     'text-brand-600',
  docs:      'text-docs-600',
  courriers: 'text-courriers-600',
  archivage: 'text-archivage-600',
};

const MODULE_DEFAULT: Record<Accent, string> = {
  brand:     '',
  docs:      'GED · Documents',
  courriers: 'GEC · Courriers',
  archivage: 'Archivage physique',
};

/**
 * En-tête de page premium. Optionnellement teinté pour identifier le module.
 *
 * Exemples :
 *   <PageHeader titre="Documents" accent="docs" icone={FileText} />
 *   <PageHeader titre="Courriers" accent="courriers" icone={Mail} />
 */
export function PageHeader({
  titre,
  sousTitre,
  actions,
  fil,
  accent,
  icone: Icone,
  module,
  className,
}: Props) {
  const moduleLabel = module ?? (accent ? MODULE_DEFAULT[accent] : '');
  const showBadge = accent && moduleLabel;

  return (
    <div className={cn('flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between', className)}>
      <div className="space-y-2">
        {fil}
        {showBadge && (
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider',
              ACCENT_BADGE[accent!],
            )}
          >
            {Icone && <Icone className={cn('h-3 w-3', ACCENT_ICON[accent!])} />}
            {moduleLabel}
          </span>
        )}
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{titre}</h1>
        {sousTitre && <p className="text-sm text-slate-500 max-w-2xl">{sousTitre}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}
