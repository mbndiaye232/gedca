import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3, Download, RefreshCw } from 'lucide-react';
import { lireActiviteAgents, type StatistiquesActiviteAgent } from '@/api/statistiques';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardBody } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { extraireMessageErreur } from '@/api/client';

/**
 * Page Statistiques d'activité (superviseur).
 *
 * Affiche par agent les compteurs des actions effectuées sur la période
 * choisie. Par défaut, la période va du début d'exploitation du logiciel
 * (date du premier courrier créé dans le tenant) jusqu'à aujourd'hui.
 *
 * L'utilisateur peut restreindre la période en saisissant date de début
 * et/ou date de fin. Bouton "Exporter en CSV" pour partager.
 */
export default function Statistiques() {
  const [dateDebut, setDateDebut] = useState<string>('');
  const [dateFin, setDateFin] = useState<string>('');

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['statistiques', 'activite-agents', dateDebut, dateFin],
    queryFn: () =>
      lireActiviteAgents(dateDebut || undefined, dateFin || undefined),
  });

  const totaux = useMemo(() => {
    if (!data) return null;
    const cumul = (k: keyof StatistiquesActiviteAgent) =>
      data.agents.reduce((acc, a) => acc + (a[k] as number), 0);
    return {
      crees: cumul('courriers_crees'),
      envoyes: cumul('courriers_envoyes'),
      en_retard: cumul('courriers_en_retard'),
      a_traiter: cumul('courriers_a_traiter'),
    };
  }, [data]);

  function exporterCSV() {
    if (!data) return;
    const headers = [
      'Agent', 'Département', 'Fonction',
      'Courriers créés', 'Mises en copie', 'Imputations émises',
      'Réponses créées', 'Courriers envoyés', 'Notes ajoutées',
      'Documents ajoutés', 'Validations demandées', 'Validations accordées',
      'À traiter (actuel)', 'En retard (actuel)',
    ];
    const lignes = data.agents.map((a) => [
      `${a.prenom} ${a.nom}`,
      a.departement ?? '',
      a.fonction ?? '',
      a.courriers_crees,
      a.mises_en_copie,
      a.imputations_emises,
      a.reponses_creees,
      a.courriers_envoyes,
      a.notes_ajoutees,
      a.documents_ajoutes,
      a.validations_demandees,
      a.validations_accordees,
      a.courriers_a_traiter,
      a.courriers_en_retard,
    ]);
    const csv = [headers, ...lignes]
      .map((row) =>
        row
          .map((cell) => {
            const s = String(cell ?? '');
            return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
          })
          .join(','),
      )
      .join('\n');
    // BOM UTF-8 pour bonne lecture des accents dans Excel
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `statistiques_activite_${data.date_debut}_${data.date_fin}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        titre="Statistiques d'activité"
        sousTitre="Compteurs des actions effectuées par chaque agent sur la période choisie."
        actions={
          <Button
            variante="secondaire"
            onClick={exporterCSV}
            disabled={!data || data.agents.length === 0}
          >
            <Download className="h-4 w-4" /> Exporter en CSV
          </Button>
        }
      />

      {/* Filtre de période */}
      <Card>
        <CardBody className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
            <div className="flex-1">
              <Input
                label="Du"
                type="date"
                value={dateDebut}
                onChange={(e) => setDateDebut(e.target.value)}
                max={dateFin || undefined}
              />
            </div>
            <div className="flex-1">
              <Input
                label="Au"
                type="date"
                value={dateFin}
                onChange={(e) => setDateFin(e.target.value)}
                min={dateDebut || undefined}
              />
            </div>
            <div className="flex gap-2">
              <Button
                variante="secondaire"
                onClick={() => {
                  setDateDebut('');
                  setDateFin('');
                }}
                title="Réinitialiser sur le début d'exploitation → aujourd'hui"
              >
                <RefreshCw className="h-4 w-4" /> Période par défaut
              </Button>
              <Button onClick={() => refetch()} chargement={isFetching}>
                Appliquer
              </Button>
            </div>
          </div>
          {data && (
            <p className="text-xs text-slate-500 mt-3">
              Période analysée : du{' '}
              <strong className="text-slate-700">{data.date_debut}</strong> au{' '}
              <strong className="text-slate-700">{data.date_fin}</strong>
              {!dateDebut && (
                <span className="text-slate-400">
                  {' '}— par défaut, depuis le premier courrier enregistré dans Soft GEDCAP
                </span>
              )}
            </p>
          )}
        </CardBody>
      </Card>

      {/* Totaux */}
      {totaux && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <TotalCard label="Courriers créés" valeur={totaux.crees} ton="bg-brand-50 text-brand-700 ring-brand-200" />
          <TotalCard label="Courriers envoyés" valeur={totaux.envoyes} ton="bg-emerald-50 text-emerald-700 ring-emerald-200" />
          <TotalCard label="À traiter (actuel)" valeur={totaux.a_traiter} ton="bg-sky-50 text-sky-700 ring-sky-200" />
          <TotalCard label="En retard (actuel)" valeur={totaux.en_retard} ton="bg-red-50 text-red-700 ring-red-200" />
        </div>
      )}

      {/* Tableau d'activité */}
      <Card className="overflow-hidden">
        {isLoading ? (
          <p className="p-8 text-center text-sm text-slate-500">Chargement…</p>
        ) : error ? (
          <p className="p-8 text-center text-sm text-red-600">
            {extraireMessageErreur(error)}
          </p>
        ) : !data || data.agents.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <BarChart3 className="h-10 w-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm">Aucune activité sur la période choisie.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/70">
                  <Th>Agent</Th>
                  <ThNum>Créés</ThNum>
                  <ThNum>Imputés</ThNum>
                  <ThNum>En copie</ThNum>
                  <ThNum>Réponses</ThNum>
                  <ThNum>Envoyés</ThNum>
                  <ThNum>Notes</ThNum>
                  <ThNum>Doc.</ThNum>
                  <ThNum>Demande val.</ThNum>
                  <ThNum>Validations</ThNum>
                  <ThNum>À traiter</ThNum>
                  <ThNum>En retard</ThNum>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.agents.map((a) => (
                  <LigneAgent key={a.agent_id} agent={a} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
      {children}
    </th>
  );
}
function ThNum({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-slate-500">
      {children}
    </th>
  );
}

function TotalCard({
  label,
  valeur,
  ton,
}: {
  label: string;
  valeur: number;
  ton: string;
}) {
  return (
    <Card>
      <CardBody className="p-4">
        <div className="flex items-start gap-3">
          <div className={`h-9 w-9 rounded-xl ring-1 ring-inset flex items-center justify-center ${ton}`}>
            <BarChart3 className="h-4 w-4" />
          </div>
          <div className="flex-1">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              {label}
            </p>
            <p className="mt-0.5 text-2xl font-bold text-slate-900 tracking-tight">
              {valeur}
            </p>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function LigneAgent({ agent }: { agent: StatistiquesActiviteAgent }) {
  return (
    <tr className="hover:bg-slate-50/50 transition-colors">
      <td className="px-4 py-3.5">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 shrink-0 rounded-full bg-gradient-brand text-white text-[10px] font-bold flex items-center justify-center">
            {agent.prenom[0]?.toUpperCase()}
            {agent.nom[0]?.toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-slate-900 font-medium truncate">
              {agent.prenom} {agent.nom}
            </p>
            <p className="text-xs text-slate-500 truncate">
              {agent.departement ?? '—'}
              {agent.fonction ? ` · ${agent.fonction}` : ''}
            </p>
          </div>
        </div>
      </td>
      <Num v={agent.courriers_crees} />
      <Num v={agent.imputations_emises} />
      <Num v={agent.mises_en_copie} />
      <Num v={agent.reponses_creees} />
      <Num v={agent.courriers_envoyes} />
      <Num v={agent.notes_ajoutees} />
      <Num v={agent.documents_ajoutes} />
      <Num v={agent.validations_demandees} />
      <Num v={agent.validations_accordees} />
      <td className="px-3 py-3.5 text-right">
        {agent.courriers_a_traiter > 0 ? (
          <Badge variante="info" pastille>
            {agent.courriers_a_traiter}
          </Badge>
        ) : (
          <span className="text-slate-300">0</span>
        )}
      </td>
      <td className="px-3 py-3.5 text-right">
        {agent.courriers_en_retard > 0 ? (
          <Badge variante="erreur" pastille>
            {agent.courriers_en_retard}
          </Badge>
        ) : (
          <span className="text-slate-300">0</span>
        )}
      </td>
    </tr>
  );
}

function Num({ v }: { v: number }) {
  return (
    <td className="px-3 py-3.5 text-right font-mono text-sm">
      {v > 0 ? (
        <span className="text-slate-900 font-semibold">{v}</span>
      ) : (
        <span className="text-slate-300">0</span>
      )}
    </td>
  );
}
