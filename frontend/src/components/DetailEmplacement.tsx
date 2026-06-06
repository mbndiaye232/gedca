import { Building2, Folder, FolderTree, Map, MapPin, Package } from 'lucide-react';
import type { EmplacementResume, NiveauResume } from '@/api/types';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';

interface Props {
  ouvert: boolean;
  emplacement: EmplacementResume | null;
  onFermer: () => void;
}

interface NiveauAffiche {
  ordre: number;
  nomNiveau: string;
  largeurNumero: 2 | 3;
  niveau: NiveauResume;
  icone: typeof MapPin;
  ton: string;
}

/**
 * Modal de détail d'un emplacement physique.
 * Affiche les 6 niveaux avec leur code dotté progressif et leur libellé.
 */
export function DetailEmplacement({ ouvert, emplacement, onFermer }: Props) {
  if (!emplacement) return null;

  const niveaux: NiveauAffiche[] = [
    { ordre: 1, nomNiveau: 'Site', largeurNumero: 2, niveau: emplacement.site, icone: Map, ton: 'bg-brand-50 text-brand-700 ring-brand-200' },
    { ordre: 2, nomNiveau: 'Local / salle', largeurNumero: 2, niveau: emplacement.local, icone: Building2, ton: 'bg-sky-50 text-sky-700 ring-sky-200' },
    { ordre: 3, nomNiveau: 'Rayon', largeurNumero: 2, niveau: emplacement.rayon, icone: FolderTree, ton: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
    { ordre: 4, nomNiveau: 'Boîte', largeurNumero: 3, niveau: emplacement.boite, icone: Package, ton: 'bg-amber-50 text-amber-700 ring-amber-200' },
    { ordre: 5, nomNiveau: 'Dossier', largeurNumero: 2, niveau: emplacement.dossier, icone: Folder, ton: 'bg-rose-50 text-rose-700 ring-rose-200' },
    { ordre: 6, nomNiveau: 'Sous-dossier', largeurNumero: 2, niveau: emplacement.sous_dossier, icone: Folder, ton: 'bg-violet-50 text-violet-700 ring-violet-200' },
  ];

  function codeAccumule(jusqua: number): string {
    return niveaux
      .slice(0, jusqua)
      .map((n) => String(n.niveau.numero).padStart(n.largeurNumero, '0'))
      .join('.');
  }

  return (
    <Modal
      ouvert={ouvert}
      onFermer={onFermer}
      titre="Détail de l'emplacement physique"
      largeur="md"
    >
      <div className="space-y-5">
        {/* Code complet en grand */}
        <div className="rounded-xl bg-gradient-to-br from-brand-50 to-white border border-brand-100 p-4 flex items-center gap-3">
          <MapPin className="h-8 w-8 text-brand-600 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-brand-700">
              Code complet
            </p>
            <p className="font-mono text-lg font-bold text-slate-900 tracking-tight mt-0.5">
              {emplacement.code_complet}
            </p>
          </div>
        </div>

        {/* Liste des 6 niveaux */}
        <div className="space-y-2">
          {niveaux.map((n, i) => (
            <div
              key={n.ordre}
              className="relative flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-3"
            >
              {/* Trait vertical reliant les niveaux */}
              {i < niveaux.length - 1 && (
                <span
                  className="absolute left-[1.5rem] top-12 h-3 w-px bg-slate-200"
                  aria-hidden
                />
              )}
              <div
                className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ring-1 ring-inset ${n.ton}`}
              >
                <n.icone className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    {n.ordre}. {n.nomNiveau}
                  </p>
                  <p className="font-mono text-xs text-slate-500">
                    {codeAccumule(i + 1)}
                  </p>
                </div>
                <p className="text-sm font-medium text-slate-900 mt-0.5 truncate">
                  {n.niveau.libelle}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end pt-2 border-t border-slate-100">
          <Button variante="secondaire" onClick={onFermer}>
            Fermer
          </Button>
        </div>
      </div>
    </Modal>
  );
}
