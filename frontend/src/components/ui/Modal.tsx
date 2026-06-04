import { useEffect, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModalProps {
  ouvert: boolean;
  onFermer: () => void;
  titre: string;
  children: ReactNode;
  largeur?: 'sm' | 'md' | 'lg';
}

const tailles = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-3xl',
};

export function Modal({ ouvert, onFermer, titre, children, largeur = 'md' }: ModalProps) {
  useEffect(() => {
    if (!ouvert) return;
    const onEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onFermer();
    };
    document.addEventListener('keydown', onEscape);
    return () => document.removeEventListener('keydown', onEscape);
  }, [ouvert, onFermer]);

  if (!ouvert) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onFermer}
    >
      <div
        className={cn(
          'w-full bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]',
          tailles[largeur],
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{titre}</h2>
          <button
            type="button"
            onClick={onFermer}
            className="p-1 rounded hover:bg-gray-100 text-gray-500"
            aria-label="Fermer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-6 py-4 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
