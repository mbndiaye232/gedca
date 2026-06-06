import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { lireMonProfil, majMonProfil } from '@/api/agents';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
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
    onError: (err) => setMessage({ type: 'erreur', text: extraireMessageErreur(err) }),
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
    return <div className="p-6 text-slate-500 text-sm">Chargement…</div>;
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <PageHeader titre="Mon profil" sousTitre="Gère tes informations et ton mot de passe." />

      {/* Carte d'identité visuelle */}
      <Card>
        <CardBody className="p-6 flex items-center gap-5">
          <div className="h-20 w-20 rounded-2xl bg-gradient-brand shadow-soft flex items-center justify-center text-white text-2xl font-bold tracking-tight">
            {profil.prenom[0]?.toUpperCase()}
            {profil.nom[0]?.toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">
              {profil.prenom} {profil.nom}
            </h2>
            <p className="text-sm text-slate-500 mt-0.5">{profil.fonction ?? '—'}</p>
            <div className="flex items-center gap-2 mt-3">
              <Badge variante="violet">{ROLE_LABELS[roleFromId(profil.role_id)]}</Badge>
              <span className="text-xs text-slate-400 font-mono">{profil.login}</span>
            </div>
          </div>
          <div className="text-right hidden sm:block">
            <p className="text-xs text-slate-400 uppercase tracking-wider">Dernière connexion</p>
            <p className="text-sm text-slate-700 mt-1">{formatDateTime(profil.derniere_connexion)}</p>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Coordonnées</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={onSubmit} className="space-y-5">
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

            <div className="pt-4 border-t border-slate-100">
              <h3 className="text-sm font-semibold text-slate-900 mb-3 tracking-tight">
                Changer mon mot de passe
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
                  label="Confirmer"
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

            <div className="flex justify-end pt-2 border-t border-slate-100">
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
