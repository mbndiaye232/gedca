import { useState, useEffect, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Building2 } from 'lucide-react';
import { lireStructure, majStructure } from '@/api/structure';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { PageHeader } from '@/components/ui/PageHeader';
import { extraireMessageErreur } from '@/api/client';

export default function Structure() {
  const queryClient = useQueryClient();
  const { data: structure, isLoading } = useQuery({
    queryKey: ['structure'],
    queryFn: lireStructure,
  });

  const [raisonSociale, setRaisonSociale] = useState('');
  const [adresse, setAdresse] = useState('');
  const [telephone, setTelephone] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState<{ type: 'succes' | 'erreur'; text: string } | null>(null);

  useEffect(() => {
    if (structure) {
      setRaisonSociale(structure.raison_sociale);
      setAdresse(structure.adresse ?? '');
      setTelephone(structure.telephone ?? '');
      setEmail(structure.email ?? '');
    }
  }, [structure]);

  const mutation = useMutation({
    mutationFn: majStructure,
    onSuccess: () => {
      setMessage({ type: 'succes', text: 'Structure mise à jour' });
      queryClient.invalidateQueries({ queryKey: ['structure'] });
    },
    onError: (err) => setMessage({ type: 'erreur', text: extraireMessageErreur(err) }),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    mutation.mutate({
      raison_sociale: raisonSociale,
      adresse: adresse || null,
      telephone: telephone || null,
      email: email || null,
    });
  }

  if (isLoading || !structure) {
    return <div className="p-6 text-slate-500 text-sm">Chargement…</div>;
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <PageHeader
        titre="Structure"
        sousTitre={`Informations de l'organisation. Code interne : ${structure.code}`}
      />

      {/* Carte d'identité visuelle */}
      <Card>
        <CardBody className="p-6 flex items-center gap-4">
          <div className="h-16 w-16 rounded-2xl bg-gradient-brand shadow-soft flex items-center justify-center text-white">
            <Building2 className="h-8 w-8" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900 tracking-tight">
              {structure.raison_sociale}
            </h2>
            <p className="text-sm text-slate-500">
              {structure.email ?? 'Aucun email configuré'}
            </p>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Informations générales</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={onSubmit} className="space-y-4">
            <Input
              label="Raison sociale *"
              value={raisonSociale}
              onChange={(e) => setRaisonSociale(e.target.value)}
              required
            />
            <Input
              label="Adresse"
              value={adresse}
              onChange={(e) => setAdresse(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Téléphone"
                type="tel"
                value={telephone}
                onChange={(e) => setTelephone(e.target.value)}
              />
              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
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
