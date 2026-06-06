import { forwardRef, type SelectHTMLAttributes } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  erreur?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, label, erreur, id, children, ...rest },
  ref,
) {
  const selectId = id ?? `select-${Math.random().toString(36).slice(2, 9)}`;
  return (
    <div className="space-y-1.5">
      {label && (
        <label
          htmlFor={selectId}
          className="block text-xs font-medium text-slate-700 tracking-wide"
        >
          {label}
        </label>
      )}
      <div className="relative">
        <select
          id={selectId}
          ref={ref}
          className={cn(
            'block w-full appearance-none rounded-lg border bg-white pl-3 pr-9 py-2.5 text-sm shadow-sm transition-shadow',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500',
            'disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed',
            erreur ? 'border-red-300' : 'border-slate-200',
            className,
          )}
          {...rest}
        >
          {children}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400"
          aria-hidden
        />
      </div>
      {erreur && <p className="text-xs text-red-600">{erreur}</p>}
    </div>
  );
});
