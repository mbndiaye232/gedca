import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  erreur?: string;
  /** Icône affichée à gauche, dans le padding. */
  icone?: ReactNode;
  /** Bouton/élément affiché à droite. */
  suffixe?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, label, erreur, id, icone, suffixe, ...rest },
  ref,
) {
  const inputId = id ?? `input-${Math.random().toString(36).slice(2, 9)}`;
  return (
    <div className="space-y-1.5">
      {label && (
        <label
          htmlFor={inputId}
          className="block text-xs font-medium text-slate-700 tracking-wide"
        >
          {label}
        </label>
      )}
      <div className="relative">
        {icone && (
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
            {icone}
          </div>
        )}
        <input
          id={inputId}
          ref={ref}
          className={cn(
            'block w-full rounded-lg border bg-white text-sm shadow-sm transition-shadow',
            'placeholder:text-slate-400',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500',
            'disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed',
            icone ? 'pl-10' : 'pl-3',
            suffixe ? 'pr-10' : 'pr-3',
            'py-2.5',
            erreur ? 'border-red-300 focus:border-red-500 focus:ring-red-500/40' : 'border-slate-200',
            className,
          )}
          {...rest}
        />
        {suffixe && (
          <div className="absolute inset-y-0 right-0 flex items-center pr-2">{suffixe}</div>
        )}
      </div>
      {erreur && <p className="text-xs text-red-600 flex items-center gap-1">{erreur}</p>}
    </div>
  );
});
