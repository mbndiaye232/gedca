import { type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Props {
  icone: LucideIcon;
  titre: string;
  message?: string;
  action?: React.ReactNode;
  className?: string;
}

/**
 * État vide premium — icône en pastille avec halo, titre, message, action.
 */
export function EmptyState({ icone: Icone, titre, message, action, className }: Props) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center py-14 px-6',
        className,
      )}
    >
      <div className="relative">
        <div
          className="absolute inset-0 -m-3 rounded-2xl bg-gradient-to-br from-brand-100 to-transparent blur-xl opacity-60"
          aria-hidden
        />
        <div className="relative inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-white shadow-sm ring-1 ring-slate-200 text-slate-400">
          <Icone className="h-7 w-7" />
        </div>
      </div>
      <h3 className="mt-4 text-base font-semibold text-slate-900 tracking-tight">{titre}</h3>
      {message && <p className="mt-1 text-sm text-slate-500 max-w-md">{message}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
