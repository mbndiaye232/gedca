import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Ban, LayoutGrid, Pencil, Plus } from 'lucide-react';
import {
  creerDepartement,
  desactiverDepartement,
  listerDepartements,
  majDepartement,
} from '@/api/departements';
import type { Departement } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { extraireMessageErreur } from '@/api/client';

export default function Departements() {
  const queryClient = useQueryClient();
  const { data: departements = [], isLoading } = useQuery({
    queryKey: ['departements'],
    queryFn: listerDepartements,
  });

  const [modalOuvert, setModalOuvert] = useState(false);
  const [enEdition, setEnEdition] = useState<Departement | null>(null);

  const desactivation = useMutation({
    mutationFn: desactiverDepartement,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['departements'] }),
    onError: (err) => alert(extraireMessageErreur(err)),
  });

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        titre="Départements"
        sousTitre="Services de l'organisation auxquels les agents sont affectés."
        actions={
          <Button onClick={() => { setEnEdition(null); setModalOuvert(true); }}>
            <Plus className="h-4 w-4" /> Nouveau département
          </Button>
        }
      />

      <Card className="overflow-hidden">
        {isLoading && <div className="p-8 text-center text-slate-500 text-sm">Chargement…</div>}
        {!isLoading && departements.length === 0 && (
          <EmptyState
            icone={LayoutGrid}
            titre="Aucun département"
            message="Crée le premier service avec « Nouveau département »."
            action={
              <Button onClick={() => { setEnEdition(null); setModalOuvert(true); }}>
                <Plus className="h-4 w-4" /> Nouveau département
              </Button>
            }
          />
        )}
        {!isLoading && departements.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50">
                <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Code
                </th>
                <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Libellé
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
              {departements.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-600">{d.code ?? '—'}</td>
                  <td className="px-5 py-3.5 text-slate-900 font-medium">{d.libelle}</td>
                  <td className="px-5 py-3.5">
                    {d.actif ? (
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
                        onClick={() => { setEnEdition(d); setModalOuvert(true); }}
                        title="Modifier"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      {d.actif && (
                        <Button
                          variante="fantome"
                          taille="sm"
                          onClick={() => {
                            if (confirm(`Désactiver le département « ${d.libelle} » ?`)) {
                              desactivation.mutate(d.id);
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
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <ModalDepartement
        ouvert={modalOuvert}
        onFermer={() => setModalOuvert(false)}
        departement={enEdition}
      />
    </div>
  );
}

interface ModalDepProps {
  ouvert: boolean;
  onFermer: () => void;
  departement: Departement | null;
}

function ModalDepartement({ ouvert, onFermer, departement }: ModalDepProps) {
  const queryClient = useQueryClient();
  const enEdition = departement !== null;

  const [code, setCode] = useState(departement?.code ?? '');
  const [libelle, setLibelle] = useState(departement?.libelle ?? '');
  const [erreur, setErreur] = useState<string | null>(null);

  if (ouvert && enEdition && departement && libelle !== departement.libelle && code !== departement.code) {
    setCode(departement.code ?? '');
    setLibelle(departement.libelle);
    setErreur(null);
  }

  const creation = useMutation({
    mutationFn: creerDepartement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['departements'] });
      setCode(''); setLibelle('');
      onFermer();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  const edition = useMutation({
    mutationFn: (params: { id: number; body: Parameters<typeof majDepartement>[1] }) =>
      majDepartement(params.id, params.body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['departements'] });
      onFermer();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    if (enEdition && departement) {
      edition.mutate({ id: departement.id, body: { code: code || null, libelle } });
    } else {
      creation.mutate({ code: code || null, libelle });
    }
  }

  return (
    <Modal
      ouvert={ouvert}
      onFermer={onFermer}
      titre={enEdition ? `Modifier ${departement?.libelle}` : 'Nouveau département'}
      largeur="sm"
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <Input
          label="Code (optionnel)"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="ex. DG"
        />
        <Input
          label="Libellé *"
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          required
        />
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button type="button" variante="secondaire" onClick={onFermer}>Annuler</Button>
          <Button type="submit" chargement={creation.isPending || edition.isPending}>
            {enEdition ? 'Enregistrer' : 'Créer'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
