import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listerAuditLog } from '@/api/audit';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Journal d'audit</h1>
        <p className="text-gray-600 text-sm mt-1">
          Trace de toutes les actions sensibles sur le tenant.
        </p>
      </div>

      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
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
      </Card>

      <Card>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3">Horodatage</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Entité</th>
              <th className="px-4 py-3">Agent</th>
              <th className="px-4 py-3">IP</th>
              <th className="px-4 py-3">Payload</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  Chargement…
                </td>
              </tr>
            )}
            {!isLoading && items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  Aucune entrée pour ces critères.
                </td>
              </tr>
            )}
            {items.map((entry) => (
              <tr key={entry.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                  {formatDateTime(entry.ts)}
                </td>
                <td className="px-4 py-3">
                  <Badge variante={entry.action.includes('echec') ? 'erreur' : 'neutre'}>
                    {entry.action}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {entry.entite ? `${entry.entite}${entry.entite_id ? ` #${entry.entite_id}` : ''}` : '—'}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {entry.agent_id ?? '—'}
                </td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{entry.ip ?? '—'}</td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs max-w-xs truncate" title={JSON.stringify(entry.payload)}>
                  {Object.keys(entry.payload).length > 0 ? JSON.stringify(entry.payload) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="flex items-center justify-between text-sm">
        <p className="text-gray-600">
          {total > 0 ? `${total} entrée(s), page ${pageActuelle} / ${pageTotal}` : ''}
        </p>
        <div className="flex gap-2">
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
      </div>
    </div>
  );
}
