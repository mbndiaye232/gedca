import { type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type Variante = 'neutre' | 'succes' | 'attention' | 'erreur' | 'info' | 'violet';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variante?: Variante;
  pastille?: boolean;
}

const variantes: Record<Variante, string> = {
  neutre: 'bg-slate-100 text-slate-700 ring-slate-200',
  succes: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  attention: 'bg-amber-50 text-amber-800 ring-amber-200',
  erreur: 'bg-red-50 text-red-800 ring-red-200',
  info: 'bg-sky-50 text-sky-800 ring-sky-200',
  violet: 'bg-brand-50 text-brand-800 ring-brand-200',
};

const pastilles: Record<Variante, string> = {
  neutre: 'bg-slate-400',
  succes: 'bg-emerald-500',
  attention: 'bg-amber-500',
  erreur: 'bg-red-500',
  info: 'bg-sky-500',
  violet: 'bg-brand-500',
};

export function Badge({
  className,
  variante = 'neutre',
  pastille,
  children,
  ...rest
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        'ring-1 ring-inset',
        variantes[variante],
        className,
      )}
      {...rest}
    >
      {pastille && <span className={cn('h-1.5 w-1.5 rounded-full', pastilles[variante])} />}
      {children}
    </span>
  );
}
