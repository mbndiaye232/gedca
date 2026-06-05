import { type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Props {
  libelle: string;
  valeur: string | number;
  icone: LucideIcon;
  /** Couleur d'accent pour l'icône. */
  ton?: 'brand' | 'sky' | 'emerald' | 'amber' | 'red' | 'slate';
  /** Texte secondaire (sous la valeur). */
  legende?: string;
  /** Variation par rapport à la période précédente (ex. '+12%'). */
  variation?: string;
  variationPositive?: boolean;
  className?: string;
}

const tons = {
  brand: 'from-brand-50 to-white text-brand-600 ring-brand-100',
  sky: 'from-sky-50 to-white text-sky-600 ring-sky-100',
  emerald: 'from-emerald-50 to-white text-emerald-600 ring-emerald-100',
  amber: 'from-amber-50 to-white text-amber-600 ring-amber-100',
  red: 'from-red-50 to-white text-red-600 ring-red-100',
  slate: 'from-slate-50 to-white text-slate-600 ring-slate-100',
} as const;

/**
 * Carte KPI premium — icône en pastille, valeur en gros chiffres,
 * variation éventuelle. Largement réutilisable sur les dashboards.
 */
export function StatsCard({
  libelle,
  valeur,
  icone: Icone,
  ton = 'brand',
  legende,
  variation,
  variationPositive,
  className,
}: Props) {
  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-card',
        'transition-shadow hover:shadow-card-hover',
        className,
      )}
    >
      {/* Halo de fond */}
      <div
        className={cn(
          'absolute -top-12 -right-12 h-32 w-32 rounded-full bg-gradient-to-br opacity-60',
          tons[ton].split(' ').slice(0, 2).join(' '),
        )}
        aria-hidden
      />
      <div className="relative p-5">
        <div className="flex items-center justify-between mb-3">
          <div
            className={cn(
              'inline-flex h-10 w-10 items-center justify-center rounded-xl ring-1 ring-inset bg-white shadow-sm',
              tons[ton].split(' ').slice(2).join(' '),
            )}
          >
            <Icone className="h-5 w-5" />
          </div>
          {variation && (
            <span
              className={cn(
                'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
                variationPositive
                  ? 'bg-emerald-50 text-emerald-700 ring-emerald-200'
                  : 'bg-red-50 text-red-700 ring-red-200',
              )}
            >
              {variation}
            </span>
          )}
        </div>
        <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{libelle}</p>
        <p className="mt-1 text-3xl font-bold text-slate-900 tracking-tight">{valeur}</p>
        {legende && <p className="mt-1 text-xs text-slate-500">{legende}</p>}
      </div>
    </div>
  );
}
