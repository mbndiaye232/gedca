import { useEffect, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModalProps {
  ouvert: boolean;
  onFermer: () => void;
  titre: string;
  children: ReactNode;
  largeur?: 'sm' | 'md' | 'lg' | 'xl';
}

const tailles = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-3xl',
  xl: 'max-w-5xl',
};

export function Modal({ ouvert, onFermer, titre, children, largeur = 'md' }: ModalProps) {
  useEffect(() => {
    if (!ouvert) return;
    const onEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onFermer();
    };
    document.addEventListener('keydown', onEscape);
    // Bloque le scroll de la page
    const original = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onEscape);
      document.body.style.overflow = original;
    };
  }, [ouvert, onFermer]);

  if (!ouvert) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4 animate-fade-in"
      onClick={onFermer}
    >
      <div
        className={cn(
          'w-full bg-white rounded-2xl shadow-elevated overflow-hidden flex flex-col max-h-[90vh] animate-scale-in',
          tailles[largeur],
        )}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-semibold text-slate-900 tracking-tight">{titre}</h2>
          <button
            type="button"
            onClick={onFermer}
            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
            aria-label="Fermer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-6 py-5 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
