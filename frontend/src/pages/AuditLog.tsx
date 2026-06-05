import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ListChecks } from 'lucide-react';
import { listerAuditLog } from '@/api/audit';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardBody } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatDateTime } from '@/lib/utils';

const LIMIT = 50;

export default function AuditLog() {
  const [action, setAction] = useState('');
  const [entite, setEntite] = useState('');
  const [offset, setOffset] = useState(0);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['audit-log', { action, entite, offset }],
    queryFn: () =>
      listerAuditLog({
        action: action || undefined,
        entite: entite || undefined,
        limit: LIMIT,
        offset,
      }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageActuelle = Math.floor(offset / LIMIT) + 1;
  const pageTotal = Math.max(1, Math.ceil(total / LIMIT));

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        titre="Journal d'audit"
        sousTitre="Trace de toutes les actions sensibles effectuées sur ce tenant."
      />

      <Card>
        <CardBody className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Action"
              placeholder="ex. login, agent.create"
              value={action}
              onChange={(e) => { setAction(e.target.value); setOffset(0); }}
            />
            <Input
              label="Entité"
              placeholder="ex. agents, departements"
              value={entite}
              onChange={(e) => { setEntite(e.target.value); setOffset(0); }}
            />
          </div>
        </CardBody>
      </Card>

      <Card className="overflow-hidden">
        {isLoading && <div className="p-8 text-center text-slate-500 text-sm">Chargement…</div>}
        {!isLoading && items.length === 0 && (
          <EmptyState
            icone={ListChecks}
            titre="Aucune entrée"
            message="Le journal d'audit se remplit dès qu'une action sensible est effectuée. Connecte-toi à nouveau pour générer une première trace."
          />
        )}
        {!isLoading && items.length > 0 && (
          <>
            <div className="px-5 py-3 border-b border-slate-100 bg-slate-50/50 text-xs text-slate-500">
              {total} entrée{total > 1 ? 's' : ''} au total · page {pageActuelle} / {pageTotal}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Horodatage
                    </th>
                    <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Action
                    </th>
                    <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Entité
                    </th>
                    <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Agent
                    </th>
                    <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      IP
                    </th>
                    <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                      Payload
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-5 py-3 text-xs text-slate-500 font-mono whitespace-nowrap">
                        {formatDateTime(entry.ts)}
                      </td>
                      <td className="px-5 py-3">
                        <Badge variante={entry.action.includes('echec') ? 'erreur' : 'info'}>
                          {entry.action}
                        </Badge>
                      </td>
                      <td className="px-5 py-3 text-slate-700 font-mono text-xs">
                        {entry.entite ? (
                          <>
                            {entry.entite}
                            {entry.entite_id !== null && (
                              <span className="text-slate-400"> #{entry.entite_id}</span>
                            )}
                          </>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="px-5 py-3 text-slate-600">{entry.agent_id ?? '—'}</td>
                      <td className="px-5 py-3 text-slate-500 font-mono text-xs">{entry.ip ?? '—'}</td>
                      <td
                        className="px-5 py-3 text-slate-500 font-mono text-xs max-w-xs truncate"
                        title={JSON.stringify(entry.payload)}
                      >
                        {Object.keys(entry.payload).length > 0
                          ? JSON.stringify(entry.payload)
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>

      {items.length > 0 && (
        <div className="flex items-center justify-end gap-2">
          <Button
            variante="secondaire"
            taille="sm"
            onClick={() => setOffset(Math.max(0, offset - LIMIT))}
            disabled={offset === 0 || isFetching}
          >
            Précédent
          </Button>
          <Button
            variante="secondaire"
            taille="sm"
            onClick={() => setOffset(offset + LIMIT)}
            disabled={offset + LIMIT >= total || isFetching}
          >
            Suivant
          </Button>
        </div>
      )}
    </div>
  );
}
