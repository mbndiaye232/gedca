import { forwardRef, type SelectHTMLAttributes } from 'react';
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
    <div className="space-y-1">
      {label && (
        <label htmlFor={selectId} className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <select
        id={selectId}
        ref={ref}
        className={cn(
          'block w-full rounded-lg border bg-white px-3 py-2 text-sm shadow-sm',
          'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent',
          erreur ? 'border-red-400' : 'border-gray-300',
          className,
        )}
        {...rest}
      >
        {children}
      </select>
      {erreur && <p className="text-xs text-red-600">{erreur}</p>}
    </div>
  );
});
