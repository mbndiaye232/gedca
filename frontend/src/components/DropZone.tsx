import { useCallback, useRef, useState, type DragEvent, type ReactNode } from 'react';
import { File as FileIcon, Upload, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Props {
  fichier: File | null;
  onChange: (fichier: File | null) => void;
  /** Texte d'invite affiché quand aucun fichier n'est sélectionné. */
  invite?: ReactNode;
  /** Accept HTML5, ex. ".pdf,.docx,image/*". */
  accept?: string;
  /** Taille max en Mo (affichage seulement, le serveur revérifie). */
  tailleMaxMo?: number;
  /** Désactive l'interaction. */
  disabled?: boolean;
  className?: string;
}

const TAILLES = ['o', 'Ko', 'Mo', 'Go'] as const;

function formatTaille(octets: number): string {
  let n = octets;
  let i = 0;
  while (n >= 1024 && i < TAILLES.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)} ${TAILLES[i]}`;
}

/**
 * Zone de glisser-déposer pour un fichier unique.
 *
 * - Drag-over : surbrillance + curseur copy.
 * - Drop : déclenche onChange(fichier).
 * - Bouton X : reset.
 */
export function DropZone({
  fichier,
  onChange,
  invite = 'Glisse un fichier ici ou clique pour sélectionner',
  accept,
  tailleMaxMo,
  disabled = false,
  className,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [survol, setSurvol] = useState(false);

  const ouvrirSelecteur = useCallback(() => {
    if (!disabled) inputRef.current?.click();
  }, [disabled]);

  const onDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setSurvol(true);
  }, [disabled]);

  const onDragLeave = useCallback(() => setSurvol(false), []);

  const onDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setSurvol(false);
      if (disabled) return;
      const f = e.dataTransfer.files?.[0];
      if (f) onChange(f);
    },
    [disabled, onChange],
  );

  if (fichier) {
    return (
      <div
        className={cn(
          'flex items-center gap-3 rounded-2xl border border-gray-200 bg-white p-4',
          className,
        )}
      >
        <FileIcon className="h-8 w-8 text-brand-700 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{fichier.name}</p>
          <p className="text-xs text-gray-500">
            {formatTaille(fichier.size)} · {fichier.type || 'type inconnu'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onChange(null)}
          className="p-1.5 rounded hover:bg-gray-100 text-gray-500"
          aria-label="Retirer le fichier"
          disabled={disabled}
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    );
  }

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={ouvrirSelecteur}
      className={cn(
        'cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-colors',
        survol
          ? 'border-brand-500 bg-brand-50'
          : 'border-gray-300 bg-gray-50 hover:bg-gray-100',
        disabled && 'cursor-not-allowed opacity-60',
        className,
      )}
    >
      <Upload className="h-10 w-10 text-gray-400 mx-auto mb-3" />
      <p className="text-sm text-gray-700">{invite}</p>
      {tailleMaxMo && (
        <p className="text-xs text-gray-500 mt-1">Taille max : {tailleMaxMo} Mo</p>
      )}
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={accept}
        disabled={disabled}
        onChange={(e) => {
          const f = e.target.files?.[0] ?? null;
          if (f) onChange(f);
        }}
      />
    </div>
  );
}
