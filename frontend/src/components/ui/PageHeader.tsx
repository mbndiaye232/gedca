import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface Props {
  titre: string;
  sousTitre?: string;
  /** Élément(s) alignés à droite (boutons d'action). */
  actions?: ReactNode;
  /** Pour ajouter un breadcrumb ou un fil au-dessus du titre. */
  fil?: ReactNode;
  className?: string;
}

/**
 * En-tête de page premium.
 * Titre tracking-tight, sous-titre slate-500, alignement actions à droite,
 * espacement vertical généreux.
 */
export function PageHeader({ titre, sousTitre, actions, fil, className }: Props) {
  return (
    <div className={cn('flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between', className)}>
      <div className="space-y-1.5">
        {fil}
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{titre}</h1>
        {sousTitre && <p className="text-sm text-slate-500 max-w-2xl">{sousTitre}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}
