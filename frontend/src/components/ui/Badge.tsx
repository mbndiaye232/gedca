import { type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

type Variante = 'neutre' | 'succes' | 'attention' | 'erreur' | 'info';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variante?: Variante;
}

const variantes: Record<Variante, string> = {
  neutre: 'bg-gray-100 text-gray-700',
  succes: 'bg-emerald-100 text-emerald-800',
  attention: 'bg-amber-100 text-amber-800',
  erreur: 'bg-red-100 text-red-800',
  info: 'bg-brand-50 text-brand-700',
};

export function Badge({ className, variante = 'neutre', ...rest }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variantes[variante],
        className,
      )}
      {...rest}
    />
  );
}
