import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { lireMonProfil, majMonProfil } from '@/api/agents';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { extraireMessageErreur } from '@/api/client';
import { ROLE_LABELS, roleFromId } from '@/api/types';
import { formatDateTime } from '@/lib/utils';

export default function Profil() {
  const queryClient = useQueryClient();
  const { data: profil, isLoading } = useQuery({
    queryKey: ['mon-profil'],
    queryFn: lireMonProfil,
  });

  const [email, setEmail] = useState('');
  const [telephone, setTelephone] = useState('');
  const [mdpActuel, setMdpActuel] = useState('');
  const [nouveauMdp, setNouveauMdp] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [message, setMessage] = useState<{ type: 'succes' | 'erreur'; text: string } | null>(null);

  // Synchroniser les champs quand le profil arrive
  if (profil && email === '' && telephone === '') {
    setEmail(profil.email ?? '');
    setTelephone(profil.telephone ?? '');
  }

  const mutation = useMutation({
    mutationFn: majMonProfil,
    onSuccess: () => {
      setMessage({ type: 'succes', text: 'Profil mis à jour' });
      setMdpActuel('');
      setNouveauMdp('');
      setConfirmation('');
      queryClient.invalidateQueries({ queryKey: ['mon-profil'] });
    },
    onError: (err) => {
      setMessage({ type: 'erreur', text: extraireMessageErreur(err) });
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);

    if (nouveauMdp && nouveauMdp !== confirmation) {
      setMessage({ type: 'erreur', text: 'Les deux mots de passe doivent être identiques' });
      return;
    }

    const body: Parameters<typeof majMonProfil>[0] = {
      email: email || null,
      telephone: telephone || null,
    };
    if (nouveauMdp) {
      body.mot_de_passe_actuel = mdpActuel;
      body.nouveau_mot_de_passe = nouveauMdp;
    }
    mutation.mutate(body);
  }

  if (isLoading || !profil) {
    return <div className="p-6 text-gray-500">Chargement…</div>;
  }

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Mon profil</h1>

      <Card>
        <CardHeader>
          <CardTitle>Informations</CardTitle>
        </CardHeader>
        <CardBody>
          <dl className="grid grid-cols-2 gap-y-3 text-sm">
            <dt className="text-gray-500">Login</dt>
            <dd className="font-mono text-gray-900">{profil.login}</dd>
            <dt className="text-gray-500">Nom</dt>
            <dd className="text-gray-900">{profil.nom}</dd>
            <dt className="text-gray-500">Prénom</dt>
            <dd className="text-gray-900">{profil.prenom}</dd>
            <dt className="text-gray-500">Fonction</dt>
            <dd className="text-gray-900">{profil.fonction ?? '—'}</dd>
            <dt className="text-gray-500">Rôle</dt>
            <dd className="text-gray-900">{ROLE_LABELS[roleFromId(profil.role_id)]}</dd>
            <dt className="text-gray-500">Dernière connexion</dt>
            <dd className="text-gray-900">{formatDateTime(profil.derniere_connexion)}</dd>
          </dl>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Modifier mes coordonnées</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={onSubmit} className="space-y-4">
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

            <div className="border-t pt-4 mt-6">
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Changer mon mot de passe (optionnel)
              </h3>
              <div className="space-y-3">
                <Input
                  label="Mot de passe actuel"
                  type="password"
                  autoComplete="current-password"
                  value={mdpActuel}
                  onChange={(e) => setMdpActuel(e.target.value)}
                />
                <Input
                  label="Nouveau mot de passe"
                  type="password"
                  autoComplete="new-password"
                  value={nouveauMdp}
                  onChange={(e) => setNouveauMdp(e.target.value)}
                  minLength={8}
                />
                <Input
                  label="Confirmer le nouveau mot de passe"
                  type="password"
                  autoComplete="new-password"
                  value={confirmation}
                  onChange={(e) => setConfirmation(e.target.value)}
                />
              </div>
            </div>

            {message && (
              <div
                className={
                  message.type === 'succes'
                    ? 'rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-700'
                    : 'rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700'
                }
              >
                {message.text}
              </div>
            )}

            <div className="flex justify-end">
              <Button type="submit" chargement={mutation.isPending}>
                Enregistrer
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
