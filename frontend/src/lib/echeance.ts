/**
 * Coloration des courriers selon la date limite.
 * Port du service backend `app/services/echeances.py`.
 *
 * Règle (PRD-01 §5.7) :
 * - noir         : date_limite < today
 * - rouge-fonce  : 0..1 jour restant
 * - rouge        : 2..3 jours restants
 * - rouge-clair  : 4 jours restants
 * - vert         : > 4 jours ou pas de date limite
 */

export type CouleurEcheance =
  | 'noir'
  | 'rouge-clair'
  | 'rouge'
  | 'rouge-fonce'
  | 'vert';

export interface StatutEcheance {
  couleur: CouleurEcheance;
  joursRestants: number | null;
}

export function calculerStatutEcheance(
  dateLimite: string | Date | null | undefined,
  aujourdHui: Date = new Date(),
  seuilAlerteJours: number = 4,
): StatutEcheance {
  if (!dateLimite) return { couleur: 'vert', joursRestants: null };

  const dl = typeof dateLimite === 'string' ? new Date(dateLimite) : dateLimite;
  if (Number.isNaN(dl.getTime())) return { couleur: 'vert', joursRestants: null };

  // Comparer au jour près, pas à l'heure
  const a = new Date(aujourdHui.getFullYear(), aujourdHui.getMonth(), aujourdHui.getDate());
  const b = new Date(dl.getFullYear(), dl.getMonth(), dl.getDate());
  const delta = Math.round((b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24));

  if (delta < 0) return { couleur: 'noir', joursRestants: delta };
  if (delta > seuilAlerteJours) return { couleur: 'vert', joursRestants: delta };
  if (delta >= 4) return { couleur: 'rouge-clair', joursRestants: delta };
  if (delta >= 2) return { couleur: 'rouge', joursRestants: delta };
  return { couleur: 'rouge-fonce', joursRestants: delta };
}

/** Renvoie les classes Tailwind associées à une couleur d'échéance. */
export function classesEcheance(couleur: CouleurEcheance): string {
  switch (couleur) {
    case 'noir':
      return 'bg-gray-900 text-white';
    case 'rouge-fonce':
      return 'bg-red-700 text-white';
    case 'rouge':
      return 'bg-red-500 text-white';
    case 'rouge-clair':
      return 'bg-red-300 text-red-900';
    case 'vert':
      return 'bg-emerald-100 text-emerald-800';
  }
}
