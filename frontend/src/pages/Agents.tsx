import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Ban, Pencil, Plus } from 'lucide-react';
import {
  creerAgent,
  desactiverAgent,
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

  function ouvrirCreation() {
    setAgentEnCours(null);
    setModalOuvert(true);
  }
  function ouvrirEdition(a: Agent) {
    setAgentEnCours(a);
    setModalOuvert(true);
  }

  const desactivation = useMutation({
    mutationFn: desactiverAgent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  });

  if (isLoading) {
    return <div className="p-6 text-gray-500">Chargement…</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Agents</h1>
          <p className="text-gray-600 text-sm mt-1">
            Gérer les comptes utilisateurs du tenant.
          </p>
        </div>
        <Button onClick={ouvrirCreation}>
          <Plus className="h-4 w-4" /> Nouvel agent
        </Button>
      </div>

      <Card>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3">Login</th>
              <th className="px-4 py-3">Nom</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Département</th>
              <th className="px-4 py-3">Rôle</th>
              <th className="px-4 py-3">Statut</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {agents.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  Aucun agent. Crée le premier avec « Nouvel agent ».
                </td>
              </tr>
            )}
            {agents.map((a) => {
              const dep = departements.find((d) => d.id === a.departement_id);
              const role = roleFromId(a.role_id);
              return (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-gray-700">{a.login}</td>
                  <td className="px-4 py-3 text-gray-900">{a.prenom} {a.nom}</td>
                  <td className="px-4 py-3 text-gray-600">{a.email ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{dep?.libelle ?? '—'}</td>
                  <td className="px-4 py-3"><Badge variante="info">{ROLE_LABELS[role]}</Badge></td>
                  <td className="px-4 py-3">
                    {a.actif ? (
                      <Badge variante="succes">Actif</Badge>
                    ) : (
                      <Badge variante="erreur">Désactivé</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex gap-2">
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
                          onClick={() => {
                            if (confirm(`Désactiver ${a.prenom} ${a.nom} ?`)) {
                              desactivation.mutate(a.id);
                            }
                          }}
                          title="Désactiver"
                        >
                          <Ban className="h-4 w-4 text-red-600" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <ModalAgent
        ouvert={modalOuvert}
        onFermer={() => setModalOuvert(false)}
        agent={agentEnCours}
        departements={departements}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Modal création / édition d'agent
// ---------------------------------------------------------------------------

interface ModalAgentProps {
  ouvert: boolean;
  onFermer: () => void;
  agent: Agent | null;
  departements: { id: number; libelle: string }[];
}

function ModalAgent({ ouvert, onFermer, agent, departements }: ModalAgentProps) {
  const queryClient = useQueryClient();
  const enEdition = agent !== null;

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

  // Reset quand on ouvre/change d'agent
  if (ouvert && enEdition && agent && login !== agent.login) {
    setLogin(agent.login);
    setNom(agent.nom);
    setPrenom(agent.prenom);
    setEmail(agent.email ?? '');
    setTelephone(agent.telephone ?? '');
    setFonction(agent.fonction ?? '');
    setDepartementId(agent.departement_id ? String(agent.departement_id) : '');
    setRole(roleFromId(agent.role_id));
    setErreur(null);
  }

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
          nom,
          prenom,
          email: email || null,
          telephone: telephone || null,
          fonction: fonction || null,
          departement_id: departementId ? Number(departementId) : null,
          role_id: ROLE_IDS[role],
        },
      });
    } else {
      creation.mutate({
        login,
        mot_de_passe: motDePasse,
        nom,
        prenom,
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
      ouvert={ouvert}
      onFermer={onFermer}
      titre={enEdition ? `Modifier ${agent?.prenom} ${agent?.nom}` : 'Nouvel agent'}
      largeur="md"
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Login *"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            disabled={enEdition}
            required
          />
          {!enEdition && (
            <Input
              label="Mot de passe initial *"
              type="password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              minLength={8}
              required
            />
          )}
          <Input
            label="Prénom *"
            value={prenom}
            onChange={(e) => setPrenom(e.target.value)}
            required
          />
          <Input
            label="Nom *"
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            required
          />
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            label="Téléphone"
            type="tel"
            value={telephone}
            onChange={(e) => setTelephone(e.target.value)}
          />
          <Input
            label="Fonction"
            value={fonction}
            onChange={(e) => setFonction(e.target.value)}
          />
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

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button
            type="submit"
            chargement={creation.isPending || edition.isPending}
          >
            {enEdition ? 'Enregistrer' : 'Créer'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
