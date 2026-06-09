import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Ban, KeyRound, Pencil, Plus, Users } from 'lucide-react';
import {
  creerAgent,
  desactiverAgent,
  initierResetMdpAgent,
  listerAgents,
  majAgent,
} from '@/api/agents';
import { listerDepartements } from '@/api/departements';
import type { Agent, Role } from '@/api/types';
import { ROLE_IDS, ROLE_LABELS, roleFromId } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { extraireMessageErreur } from '@/api/client';

export default function Agents() {
  const queryClient = useQueryClient();
  const { data: agents = [], isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: listerAgents,
  });
  const { data: departements = [] } = useQuery({
    queryKey: ['departements'],
    queryFn: listerDepartements,
  });

  const [modalOuvert, setModalOuvert] = useState(false);
  const [agentEnCours, setAgentEnCours] = useState<Agent | null>(null);

  const desactivation = useMutation({
    mutationFn: desactiverAgent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  });

  const resetMdp = useMutation({
    mutationFn: initierResetMdpAgent,
    onSuccess: (data) => {
      if (data.email_envoye) {
        alert(
          `Lien de réinitialisation envoyé à ${data.destinataire_email}.\n\n` +
            `Le lien est valable ${data.duree_validite_heures} heures et ne peut servir qu'une fois.`,
        );
      } else {
        alert(
          "Le token a été généré mais l'email n'a pas pu être envoyé. " +
            'Vérifie la configuration SMTP du tenant.',
        );
      }
    },
    onError: (err) => alert(extraireMessageErreur(err)),
  });

  function ouvrirCreation() {
    setAgentEnCours(null);
    setModalOuvert(true);
  }
  function ouvrirEdition(a: Agent) {
    setAgentEnCours(a);
    setModalOuvert(true);
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        titre="Agents"
        sousTitre="Gérer les comptes utilisateurs et leurs rôles."
        actions={
          <Button onClick={ouvrirCreation}>
            <Plus className="h-4 w-4" /> Nouvel agent
          </Button>
        }
      />

      <Card className="overflow-hidden">
        {isLoading && <div className="p-8 text-center text-slate-500 text-sm">Chargement…</div>}
        {!isLoading && agents.length === 0 && (
          <EmptyState
            icone={Users}
            titre="Aucun agent"
            message="Crée le premier compte utilisateur avec « Nouvel agent »."
            action={
              <Button onClick={ouvrirCreation}>
                <Plus className="h-4 w-4" /> Nouvel agent
              </Button>
            }
          />
        )}
        {!isLoading && agents.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50">
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Agent
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Email
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Département
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Rôle
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Statut
                  </th>
                  <th className="px-5 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {agents.map((a) => {
                  const dep = departements.find((d) => d.id === a.departement_id);
                  const role = roleFromId(a.role_id);
                  return (
                    <tr key={a.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 shrink-0 rounded-full bg-gradient-brand text-white text-[10px] font-bold flex items-center justify-center">
                            {a.prenom[0]?.toUpperCase()}
                            {a.nom[0]?.toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <p className="text-slate-900 font-medium">
                              {a.prenom} {a.nom}
                            </p>
                            <p className="text-xs text-slate-500 font-mono">{a.login}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-slate-600">{a.email ?? '—'}</td>
                      <td className="px-5 py-3.5 text-slate-600">{dep?.libelle ?? '—'}</td>
                      <td className="px-5 py-3.5">
                        <Badge variante={role === 'superviseur' ? 'violet' : 'info'}>
                          {ROLE_LABELS[role]}
                        </Badge>
                      </td>
                      <td className="px-5 py-3.5">
                        {a.actif ? (
                          <Badge variante="succes" pastille>Actif</Badge>
                        ) : (
                          <Badge variante="erreur" pastille>Désactivé</Badge>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <div className="inline-flex gap-1">
                          <Button
                            variante="fantome"
                            taille="sm"
                            onClick={() => ouvrirEdition(a)}
                            title="Modifier"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          {a.actif && (
                            <Button
                              variante="fantome"
                              taille="sm"
                              disabled={!a.email || resetMdp.isPending}
                              onClick={() => {
                                if (
                                  confirm(
                                    `Envoyer un lien de réinitialisation de mot de passe à ${a.prenom} ${a.nom} ?\n\n` +
                                      `Email destinataire : ${a.email}\n` +
                                      `Le lien sera valable 24 heures.`,
                                  )
                                ) {
                                  resetMdp.mutate(a.id);
                                }
                              }}
                              title={
                                a.email
                                  ? 'Réinitialiser le mot de passe'
                                  : "Cet agent n'a pas d'email — renseigne-le d'abord"
                              }
                            >
                              <KeyRound className="h-4 w-4 text-amber-600" />
                            </Button>
                          )}
                          {a.actif && (
                            <Button
                              variante="fantome"
                              taille="sm"
                              onClick={() => {
                                if (confirm(`Désactiver ${a.prenom} ${a.nom} ?`)) {
                                  desactivation.mutate(a.id);
                                }
                              }}
                              title="Désactiver"
                            >
                              <Ban className="h-4 w-4 text-red-500" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {modalOuvert && (
        <ModalAgent
          key={agentEnCours?.id ?? 'nouveau'}
          onFermer={() => setModalOuvert(false)}
          agent={agentEnCours}
          departements={departements}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Modal création / édition d'agent
// ---------------------------------------------------------------------------

interface ModalAgentProps {
  onFermer: () => void;
  agent: Agent | null;
  departements: { id: number; libelle: string }[];
}

function ModalAgent({ onFermer, agent, departements }: ModalAgentProps) {
  const queryClient = useQueryClient();
  const enEdition = agent !== null;

  // Le composant est remonté à chaque ouverture (cf. {modalOuvert && <ModalAgent
  // key=... />}), donc useState s'initialise toujours proprement à partir de
  // `agent` ou valeurs vides — pas besoin de useEffect ou de hack de resync.
  const [login, setLogin] = useState(agent?.login ?? '');
  const [motDePasse, setMotDePasse] = useState('');
  const [nom, setNom] = useState(agent?.nom ?? '');
  const [prenom, setPrenom] = useState(agent?.prenom ?? '');
  const [email, setEmail] = useState(agent?.email ?? '');
  const [telephone, setTelephone] = useState(agent?.telephone ?? '');
  const [fonction, setFonction] = useState(agent?.fonction ?? '');
  const [departementId, setDepartementId] = useState<string>(
    agent?.departement_id ? String(agent.departement_id) : '',
  );
  const [role, setRole] = useState<Role>(agent ? roleFromId(agent.role_id) : 'agent_standard');
  const [erreur, setErreur] = useState<string | null>(null);

  const creation = useMutation({
    mutationFn: creerAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      onFermer();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  const edition = useMutation({
    mutationFn: (params: { id: number; body: Parameters<typeof majAgent>[1] }) =>
      majAgent(params.id, params.body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      onFermer();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);

    if (enEdition && agent) {
      edition.mutate({
        id: agent.id,
        body: {
          nom, prenom,
          email: email || null,
          telephone: telephone || null,
          fonction: fonction || null,
          departement_id: departementId ? Number(departementId) : null,
          role_id: ROLE_IDS[role],
        },
      });
    } else {
      creation.mutate({
        login, mot_de_passe: motDePasse, nom, prenom,
        email: email || null,
        telephone: telephone || null,
        fonction: fonction || null,
        departement_id: departementId ? Number(departementId) : null,
        role_id: ROLE_IDS[role],
      });
    }
  }

  return (
    <Modal
      ouvert
      onFermer={onFermer}
      titre={enEdition ? `Modifier ${agent?.prenom} ${agent?.nom}` : 'Nouvel agent'}
      largeur="md"
    >
      <form onSubmit={onSubmit} className="space-y-4" autoComplete="off">
        {/* Honey-pot anti-autocomplete Chrome : ces champs cachés
            capturent l'autocomplete agressif que Chrome impose même
            quand on lui dit "off" sur le form principal. Sans ça,
            Chrome remplit le Login et le Password avec les credentials
            d'un agent récemment créé / connecté. */}
        <input
          type="text"
          name="fake-username"
          autoComplete="username"
          tabIndex={-1}
          aria-hidden="true"
          style={{ position: 'absolute', left: '-9999px', width: 0, height: 0 }}
          readOnly
        />
        <input
          type="password"
          name="fake-password"
          autoComplete="current-password"
          tabIndex={-1}
          aria-hidden="true"
          style={{ position: 'absolute', left: '-9999px', width: 0, height: 0 }}
          readOnly
        />
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Login *"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            disabled={enEdition}
            required
            // `new-password` est le seul autoComplete que Chrome
            // respecte vraiment pour empêcher le remplissage auto
            // (paradoxalement, sur le champ login aussi).
            autoComplete="new-password"
            name="agent-creation-login"
          />
          {!enEdition && (
            <Input
              label="Mot de passe initial *"
              type="password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              minLength={8}
              required
              autoComplete="new-password"
              name="agent-creation-password"
            />
          )}
          <Input label="Prénom *" value={prenom} onChange={(e) => setPrenom(e.target.value)} required />
          <Input label="Nom *" value={nom} onChange={(e) => setNom(e.target.value)} required />
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input label="Téléphone" type="tel" value={telephone} onChange={(e) => setTelephone(e.target.value)} />
          <Input label="Fonction" value={fonction} onChange={(e) => setFonction(e.target.value)} />
          <Select
            label="Département"
            value={departementId}
            onChange={(e) => setDepartementId(e.target.value)}
          >
            <option value="">— aucun —</option>
            {departements.map((d) => (
              <option key={d.id} value={d.id}>{d.libelle}</option>
            ))}
          </Select>
          <Select
            label="Rôle *"
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
            required
          >
            <option value="agent_standard">Agent</option>
            <option value="archiviste">Archiviste</option>
            <option value="superviseur">Superviseur</option>
          </Select>
        </div>

        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button type="button" variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button type="submit" chargement={creation.isPending || edition.isPending}>
            {enEdition ? 'Enregistrer' : 'Créer'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
