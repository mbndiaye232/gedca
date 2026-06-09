import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowDownLeft,
  ArrowUpRight,
  BadgeCheck,
  CheckCircle2,
  Clock,
  Copy,
  Hourglass,
  Inbox,
  Mail,
  Plus,
  RefreshCw,
  ShieldCheck,
  Stamp,
  type LucideIcon,
} from 'lucide-react';
import { compteursCorbeilles, listerCourriers } from '@/api/courriers';
import type { CorbeilleCode, Courrier, SensCourrier } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { calculerStatutEcheance, classesEcheance } from '@/lib/echeance';
import { formatDate, formatDateTime, cn } from '@/lib/utils';
import { ModalTraiter } from '@/components/ModalTraiter';

const ICONES_CORBEILLE: Record<CorbeilleCode, LucideIcon> = {
  a_traiter: Inbox,
  traite: CheckCircle2,
  en_copie: Copy,
  en_retard: Clock,
  // PRD-06B — icônes distinctes pour le workflow de validation
  a_valider: ShieldCheck,        // côté valideur : "à valider par moi"
  valides: BadgeCheck,            // côté demandeur : "validés, prêts à envoyer"
  a_faire_valider: Stamp,         // côté demandeur : "je dois faire valider"
  en_validation: Hourglass,       // côté demandeur : "en attente du valideur"
};

const TONS_CORBEILLE: Record<CorbeilleCode, string> = {
  a_traiter: 'bg-courriers-50 text-courriers-700 ring-courriers-200',
  traite: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  en_copie: 'bg-sky-50 text-sky-700 ring-sky-200',
  en_retard: 'bg-red-50 text-red-700 ring-red-200',
  // PRD-06B — tons distincts pour les 4 corbeilles validation, dans la
  // famille violet/indigo pour signaler qu'on est dans un workflow
  // d'autorisation hiérarchique (différent des urgences en rouge ou des
  // courriers ordinaires en brand).
  a_valider: 'bg-violet-50 text-violet-700 ring-violet-200',
  valides: 'bg-teal-50 text-teal-700 ring-teal-200',
  a_faire_valider: 'bg-fuchsia-50 text-fuchsia-700 ring-fuchsia-200',
  en_validation: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
};

const ICONES_SENS: Record<SensCourrier, LucideIcon> = {
  entrant: ArrowDownLeft,
  sortant: ArrowUpRight,
  interne: RefreshCw,
};

const TONS_SENS: Record<SensCourrier, string> = {
  entrant: 'bg-emerald-50 text-emerald-700',
  sortant: 'bg-sky-50 text-sky-700',
  interne: 'bg-violet-50 text-violet-700',
};

export default function Courriers() {
  const [corbeille, setCorbeille] = useState<CorbeilleCode>('a_traiter');
  const [courrierTraiter, setCourrierTraiter] = useState<number | null>(null);

  const { data: compteurs } = useQuery({
    queryKey: ['courriers', 'corbeilles'],
    queryFn: compteursCorbeilles,
    refetchInterval: 30_000,
  });

  const { data: liste = [], isLoading } = useQuery({
    queryKey: ['courriers', 'liste', corbeille],
    queryFn: () => listerCourriers(corbeille),
    enabled: !!corbeille,
  });

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        titre="Courriers"
        sousTitre="Espace de travail principal. Sélectionne une corbeille pour voir les courriers à traiter."
        accent="courriers"
        icone={Mail}
        actions={
          <Link to="/courriers/nouveau">
            <Button>
              <Plus className="h-4 w-4" /> Nouveau courrier
            </Button>
          </Link>
        }
      />

      {/* Cartes des 8 corbeilles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {compteurs?.corbeilles.map((c) => {
          const Icone = ICONES_CORBEILLE[c.code];
          const actif = corbeille === c.code;
          return (
            <button
              key={c.code}
              type="button"
              onClick={() => setCorbeille(c.code)}
              className={cn(
                'relative text-left rounded-2xl border bg-white p-4 transition-all',
                // PRD-06B : toutes les corbeilles sont cliquables (les 4
                // corbeilles validation sont désormais alimentées). Plus
                // de `cliquable`/`opacity-60` hérité de l'ère 06A.
                actif
                  ? 'border-courriers-300 shadow-card-hover ring-2 ring-courriers-100'
                  : 'border-slate-200/70 shadow-card hover:shadow-card-hover hover:border-slate-300 cursor-pointer',
              )}
            >
              <div className="flex items-center justify-between mb-3">
                <div
                  className={cn(
                    'inline-flex h-9 w-9 items-center justify-center rounded-xl ring-1 ring-inset',
                    TONS_CORBEILLE[c.code],
                  )}
                >
                  <Icone className="h-4 w-4" />
                </div>
              </div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                {c.libelle}
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-900 tracking-tight">
                {c.compteur}
              </p>
            </button>
          );
        })}
      </div>

      {/* Tableau de la corbeille active */}
      <Card className="overflow-hidden">
        {isLoading ? (
          <p className="p-8 text-center text-sm text-slate-500">Chargement…</p>
        ) : liste.length === 0 ? (
          <EmptyState
            icone={Mail}
            titre={`Aucun courrier dans la corbeille « ${libelleCorbeille(corbeille)} »`}
            message={
              corbeille === 'a_traiter'
                ? 'Profite de la tranquillité ou enregistre un nouveau courrier.'
                : undefined
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50">
                  <Th>Numéro</Th>
                  <Th>Sens</Th>
                  <Th>Objet</Th>
                  <Th>Correspondant</Th>
                  <Th>Date</Th>
                  <Th>Échéance</Th>
                  <Th>Statut</Th>
                  <Th className="text-right">Action</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {liste.map((c) => (
                  <LigneCourrier
                    key={c.id}
                    courrier={c}
                    onTraiter={() => setCourrierTraiter(c.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {courrierTraiter !== null && (
        <ModalTraiter
          ouvert
          courrierId={courrierTraiter}
          onFermer={() => setCourrierTraiter(null)}
        />
      )}
    </div>
  );
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={cn(
        'px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500',
        className,
      )}
    >
      {children}
    </th>
  );
}

function LigneCourrier({
  courrier,
  onTraiter,
}: {
  courrier: Courrier;
  onTraiter: () => void;
}) {
  const SensIcone = ICONES_SENS[courrier.sens];
  const echeance = calculerStatutEcheance(courrier.date_limite);

  function correspondantText(): string {
    if (!courrier.correspondant) return '—';
    if (courrier.correspondant.raison_sociale) return courrier.correspondant.raison_sociale;
    return `${courrier.correspondant.prenom ?? ''} ${courrier.correspondant.nom ?? ''}`.trim();
  }

  return (
    <tr className="hover:bg-slate-50/50 transition-colors">
      <td className="px-5 py-3.5 font-mono text-xs text-slate-700">
        {courrier.numero_enregistrement}
      </td>
      <td className="px-5 py-3.5">
        <div
          className={cn(
            'inline-flex h-7 w-7 items-center justify-center rounded-lg',
            TONS_SENS[courrier.sens],
          )}
          title={courrier.sens}
        >
          <SensIcone className="h-3.5 w-3.5" />
        </div>
      </td>
      <td className="px-5 py-3.5 max-w-md">
        <p className="text-slate-900 font-medium truncate" title={courrier.objet}>
          {courrier.objet}
        </p>
        {courrier.mots_cles && (
          <p className="text-xs text-slate-500 truncate" title={courrier.mots_cles}>
            {courrier.mots_cles}
          </p>
        )}
      </td>
      <td className="px-5 py-3.5 text-slate-600 max-w-xs truncate">
        {correspondantText()}
      </td>
      <td className="px-5 py-3.5 text-slate-600 text-xs">
        {formatDate(courrier.date_courrier)}
      </td>
      <td className="px-5 py-3.5">
        {courrier.date_limite ? (
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
              classesEcheance(echeance.couleur),
            )}
            title={`${echeance.joursRestants ?? '—'} jour(s)`}
          >
            {formatDate(courrier.date_limite)}
          </span>
        ) : (
          <span className="text-xs text-slate-400">—</span>
        )}
      </td>
      <td className="px-5 py-3.5">
        <StatutBadge code={courrier.statut.code} libelle={courrier.statut.libelle} />
      </td>
      <td className="px-5 py-3.5 text-right">
        <Button taille="sm" onClick={onTraiter}>
          Traiter
        </Button>
      </td>
    </tr>
  );
}

/**
 * Badge de statut courrier — palette dédiée pour chaque code (alignée
 * avec les tons des corbeilles : amber pour les états « en transit »
 * du workflow validation, vert pour les terminés, brand pour
 * « à traiter ».
 */
function StatutBadge({ code, libelle }: { code: string; libelle: string }) {
  const tons: Record<string, 'info' | 'succes' | 'attention' | 'violet' | 'neutre'> = {
    a_traiter: 'info',
    traite: 'succes',
    a_faire_valider: 'attention',
    en_validation: 'violet',
    valide: 'succes',
  };
  return (
    <Badge variante={tons[code] ?? 'neutre'} pastille>
      {libelle}
    </Badge>
  );
}

function libelleCorbeille(c: CorbeilleCode): string {
  const map: Record<CorbeilleCode, string> = {
    a_traiter: 'À traiter',
    traite: 'Traités',
    en_copie: 'En copie',
    en_retard: 'En retard',
    a_valider: 'À valider',
    valides: 'Validés',
    a_faire_valider: 'À faire valider',
    en_validation: 'En validation',
  };
  return map[c];
}
