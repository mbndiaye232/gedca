import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Plane, Plus, Trash2, UserCheck } from 'lucide-react';
import {
  creerRedirection,
  maRedirection,
  supprimerRedirection,
} from '@/api/redirections';
import { listerAgentsDestinataires } from '@/api/agents';
import { listerDepartements } from '@/api/departements';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { Card, CardBody } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { extraireMessageErreur } from '@/api/client';
import { useAuth } from '@/auth/useAuth';
import { formatDateTime } from '@/lib/utils';

/**
 * Page Redirection (docs/redirection.pdf).
 *
 * Permet à un agent de signaler son absence (congés, indisponibilité) en
 * désignant un substitut. Tout courrier qui lui sera destiné après la
 * création arrivera directement chez le substitut, jusqu'à suppression
 * de la redirection.
 *
 * Règles :
 * - Une seule redirection active à la fois (contrainte DB + UI)
 * - Choix par cascade département → agent
 * - Suppression avec confirmation explicite
 * - Les courriers déjà reçus avant la redirection ne sont pas affectés
 */
export default function Redirection() {
  const { agent } = useAuth();
  const queryClient = useQueryClient();
  const [modalOuvert, setModalOuvert] = useState(false);

  const { data: redirection, isLoading } = useQuery({
    queryKey: ['redirections', 'me'],
    queryFn: maRedirection,
  });

  const suppression = useMutation({
    mutationFn: supprimerRedirection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['redirections', 'me'] });
    },
    onError: (err) => alert(extraireMessageErreur(err)),
  });

  if (!agent) return null;

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <PageHeader
        titre="Redirection"
        sousTitre="Pendant tes congés ou ton indisponibilité, redirige tes courriers vers un collègue substitut."
        actions={
          !redirection && (
            <Button onClick={() => setModalOuvert(true)}>
              <Plus className="h-4 w-4" /> Créer une redirection
            </Button>
          )
        }
      />

      {/* État courant */}
      <Card>
        <CardBody className="p-6">
          {isLoading && (
            <p className="text-sm text-slate-500 text-center py-4">Chargement…</p>
          )}
          {!isLoading && !redirection && (
            <EmptyState
              icone={Plane}
              titre="Aucune redirection en cours"
              message="Tu es opérationnel — tu reçois tes courriers normalement. Crée une redirection avant un départ pour qu'un collègue prenne le relais."
              action={
                <Button onClick={() => setModalOuvert(true)}>
                  <Plus className="h-4 w-4" /> Créer une redirection
                </Button>
              }
            />
          )}
          {redirection && (
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="h-12 w-12 rounded-2xl bg-amber-50 ring-1 ring-amber-200 flex items-center justify-center">
                  <UserCheck className="h-6 w-6 text-amber-700" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-lg font-semibold text-slate-900">
                      Redirection active
                    </h2>
                    <Badge variante="attention" pastille>
                      En cours
                    </Badge>
                  </div>
                  <p className="text-sm text-slate-600">
                    Tes nouveaux courriers sont envoyés à{' '}
                    <strong className="text-slate-900">
                      {redirection.agent_substitut?.prenom}{' '}
                      {redirection.agent_substitut?.nom}
                    </strong>
                    {redirection.agent_substitut?.fonction && (
                      <span className="text-slate-500">
                        {' '}
                        — {redirection.agent_substitut.fonction}
                      </span>
                    )}
                    .
                  </p>
                  <p className="text-xs text-slate-500 mt-2">
                    Active depuis le {formatDateTime(redirection.cree_at)}
                  </p>
                </div>
              </div>

              <div className="rounded-lg bg-sky-50 border border-sky-200 px-3 py-2 text-xs text-sky-900">
                <strong>Important :</strong> seuls les <strong>nouveaux</strong> courriers
                sont redirigés. Ceux déjà reçus restent dans tes corbeilles et
                devront être traités à ton retour (ou imputés manuellement).
              </div>

              <div className="flex justify-end pt-2 border-t border-slate-100">
                <Button
                  variante="secondaire"
                  onClick={() => {
                    if (
                      confirm(
                        `Supprimer la redirection vers ${redirection.agent_substitut?.prenom} ${redirection.agent_substitut?.nom} ?\n\nTes prochains courriers reviendront dans tes corbeilles.`,
                      )
                    ) {
                      suppression.mutate(redirection.id);
                    }
                  }}
                  chargement={suppression.isPending}
                >
                  <Trash2 className="h-4 w-4 text-red-500" /> Supprimer la redirection
                </Button>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {modalOuvert && (
        <ModalCreerRedirection
          onFermer={() => setModalOuvert(false)}
          monAgentId={agent.id}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Modal de création — cascade département → agent
// ---------------------------------------------------------------------------

function ModalCreerRedirection({
  onFermer,
  monAgentId,
}: {
  onFermer: () => void;
  monAgentId: number;
}) {
  const queryClient = useQueryClient();
  const [departementId, setDepartementId] = useState<string>('');
  const [agentSubstitutId, setAgentSubstitutId] = useState<string>('');
  const [erreur, setErreur] = useState<string | null>(null);

  const { data: agents = [] } = useQuery({
    queryKey: ['agents', 'destinataires'],
    queryFn: listerAgentsDestinataires,
  });
  const { data: departements = [] } = useQuery({
    queryKey: ['departements'],
    queryFn: listerDepartements,
  });

  // Cascade dep → agents — on exclut moi-même (le PDF dit "vers la
  // personne de son choix", mais évidemment pas soi-même).
  const agentsFiltres = (departementId
    ? agents.filter((a) => a.departement_id === Number(departementId))
    : agents
  ).filter((a) => a.id !== monAgentId);

  const creation = useMutation({
    mutationFn: () =>
      creerRedirection({ agent_substitut_id: Number(agentSubstitutId) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['redirections', 'me'] });
      onFermer();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    if (!agentSubstitutId) {
      setErreur('Choisis un agent substitut.');
      return;
    }
    creation.mutate();
  }

  return (
    <Modal
      ouvert
      onFermer={onFermer}
      titre="Créer une redirection"
      largeur="md"
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-900 flex gap-2">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            Tu ne peux avoir qu'<strong>une seule</strong> redirection active à
            la fois. Pour en changer, supprime d'abord celle en cours.
          </div>
        </div>

        <Select
          label="Département (filtre)"
          value={departementId}
          onChange={(e) => {
            setDepartementId(e.target.value);
            setAgentSubstitutId('');
          }}
        >
          <option value="">— Tous les départements —</option>
          {departements.map((d) => (
            <option key={d.id} value={d.id}>
              {d.libelle}
            </option>
          ))}
        </Select>

        <Select
          label="Agent substitut *"
          value={agentSubstitutId}
          onChange={(e) => setAgentSubstitutId(e.target.value)}
          required
        >
          <option value="">— choisir —</option>
          {agentsFiltres.map((a) => (
            <option key={a.id} value={a.id}>
              {a.prenom} {a.nom}
              {a.fonction ? ` — ${a.fonction}` : ''}
            </option>
          ))}
        </Select>

        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button type="button" variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button
            type="submit"
            disabled={!agentSubstitutId}
            chargement={creation.isPending}
          >
            Activer la redirection
          </Button>
        </div>
      </form>
    </Modal>
  );
}
