import { useState, type FormEvent, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Ban, FolderTree, Pencil, Plus, Tag, Tags } from 'lucide-react';
import {
  creerCategorie,
  creerThematique,
  creerTypeDocument,
  listerCategories,
  listerThematiques,
  listerTypesDocument,
  majCategorie,
  majThematique,
  majTypeDocument,
  supprimerCategorie,
  supprimerThematique,
  supprimerTypeDocument,
} from '@/api/referentiels';
import type { Categorie, Referentiel } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { extraireMessageErreur } from '@/api/client';
import { cn } from '@/lib/utils';

export default function Referentiels() {
  return (
    <div className="p-6 space-y-6">
      <PageHeader
        titre="Référentiels"
        sousTitre="Catégories, thématiques et types de document utilisés pour classer les documents."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SectionCategories />
        <SectionThematiques />
        <SectionTypesDocument />
      </div>
    </div>
  );
}

// ===========================================================================
// Catégories — référentiel riche (libellé + description)
// ===========================================================================

function SectionCategories() {
  const queryClient = useQueryClient();
  const { data: items = [], isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: listerCategories,
  });

  const [modalCreation, setModalCreation] = useState(false);
  const [enEdition, setEnEdition] = useState<Categorie | null>(null);

  const supp = useMutation({
    mutationFn: supprimerCategorie,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['categories'] }),
    onError: (err) => alert(extraireMessageErreur(err)),
  });

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Tag className="h-4 w-4 text-brand-600" />
          <CardTitle>Catégories</CardTitle>
        </div>
        <Button taille="sm" onClick={() => setModalCreation(true)}>
          <Plus className="h-4 w-4" /> Ajouter
        </Button>
      </CardHeader>
      <CardBody className="p-0 flex-1">
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Chargement…</p>
        ) : items.length === 0 ? (
          <EmptyState
            icone={Tag}
            titre="Aucune catégorie"
            message="Crée la première — elle sera proposée à l'upload."
          />
        ) : (
          <ul className="divide-y divide-slate-100">
            {items.map((c) => (
              <li
                key={c.id}
                className="px-5 py-3 flex items-start gap-3 hover:bg-slate-50/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{c.libelle}</p>
                  {c.description && (
                    <p className="text-xs text-slate-500 mt-0.5 truncate">{c.description}</p>
                  )}
                </div>
                <BoutonsLigne
                  onEditer={() => setEnEdition(c)}
                  onSupprimer={() => {
                    if (confirm(`Désactiver la catégorie « ${c.libelle} » ?`)) {
                      supp.mutate(c.id);
                    }
                  }}
                />
              </li>
            ))}
          </ul>
        )}
      </CardBody>

      <ModalCategorie
        ouvert={modalCreation || enEdition !== null}
        onFermer={() => {
          setModalCreation(false);
          setEnEdition(null);
        }}
        existant={enEdition}
      />
    </Card>
  );
}

interface ModalCategorieProps {
  ouvert: boolean;
  onFermer: () => void;
  existant: Categorie | null;
}

function ModalCategorie({ ouvert, onFermer, existant }: ModalCategorieProps) {
  const queryClient = useQueryClient();
  const enEdition = existant !== null;

  const [libelle, setLibelle] = useState(existant?.libelle ?? '');
  const [description, setDescription] = useState(existant?.description ?? '');
  const [erreur, setErreur] = useState<string | null>(null);

  if (
    ouvert &&
    enEdition &&
    existant &&
    libelle !== existant.libelle &&
    description !== (existant.description ?? '')
  ) {
    // resync à l'ouverture d'une nouvelle édition
    setLibelle(existant.libelle);
    setDescription(existant.description ?? '');
    setErreur(null);
  }

  function reset() {
    setLibelle('');
    setDescription('');
    setErreur(null);
    onFermer();
  }

  const creation = useMutation({
    mutationFn: creerCategorie,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      reset();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  const edition = useMutation({
    mutationFn: (params: { id: number; body: Parameters<typeof majCategorie>[1] }) =>
      majCategorie(params.id, params.body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      reset();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    if (enEdition && existant) {
      edition.mutate({
        id: existant.id,
        body: { libelle, description: description || null },
      });
    } else {
      creation.mutate({ libelle, description: description || null });
    }
  }

  return (
    <Modal
      ouvert={ouvert}
      onFermer={reset}
      titre={enEdition ? `Modifier « ${existant?.libelle} »` : 'Nouvelle catégorie'}
      largeur="sm"
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <Input
          label="Libellé *"
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          autoFocus
          required
        />
        <Input
          label="Description (optionnel)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        {erreur && <BoiteErreur message={erreur} />}
        <ActionsModal
          onAnnuler={reset}
          chargement={creation.isPending || edition.isPending}
          libelleSubmit={enEdition ? 'Enregistrer' : 'Créer'}
        />
      </form>
    </Modal>
  );
}

// ===========================================================================
// Thématiques et Types de document — référentiels simples (libellé)
// ===========================================================================

function SectionThematiques() {
  return (
    <SectionReferentielSimple
      titre="Thématiques"
      icone={Tags}
      queryKey={['thematiques']}
      lister={listerThematiques}
      creer={creerThematique}
      majFn={majThematique}
      supprimerFn={supprimerThematique}
      libelleEmptyTitre="Aucune thématique"
      libelleEmptyMsg="Ex. Comptabilité, RH, Production…"
      libelleModalCreation="Nouvelle thématique"
      libelleType="thématique"
    />
  );
}

function SectionTypesDocument() {
  return (
    <SectionReferentielSimple
      titre="Types de document"
      icone={FolderTree}
      queryKey={['types-document']}
      lister={listerTypesDocument}
      creer={creerTypeDocument}
      majFn={majTypeDocument}
      supprimerFn={supprimerTypeDocument}
      libelleEmptyTitre="Aucun type"
      libelleEmptyMsg="Ex. Facture, Contrat, Rapport…"
      libelleModalCreation="Nouveau type"
      libelleType="type de document"
    />
  );
}

interface SectionSimpleProps {
  titre: string;
  icone: React.ComponentType<{ className?: string }>;
  queryKey: readonly unknown[];
  lister: () => Promise<Referentiel[]>;
  creer: (libelle: string) => Promise<Referentiel>;
  majFn: (id: number, libelle: string) => Promise<Referentiel>;
  supprimerFn: (id: number) => Promise<Referentiel>;
  libelleEmptyTitre: string;
  libelleEmptyMsg: string;
  libelleModalCreation: string;
  libelleType: string;
}

function SectionReferentielSimple({
  titre,
  icone: Icone,
  queryKey,
  lister,
  creer,
  majFn,
  supprimerFn,
  libelleEmptyTitre,
  libelleEmptyMsg,
  libelleModalCreation,
  libelleType,
}: SectionSimpleProps) {
  const queryClient = useQueryClient();
  const { data: items = [], isLoading } = useQuery({
    queryKey,
    queryFn: lister,
  });

  const [modalCreation, setModalCreation] = useState(false);
  const [enEdition, setEnEdition] = useState<Referentiel | null>(null);

  const supp = useMutation({
    mutationFn: supprimerFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
    onError: (err) => alert(extraireMessageErreur(err)),
  });

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Icone className="h-4 w-4 text-brand-600" />
          <CardTitle>{titre}</CardTitle>
        </div>
        <Button taille="sm" onClick={() => setModalCreation(true)}>
          <Plus className="h-4 w-4" /> Ajouter
        </Button>
      </CardHeader>
      <CardBody className="p-0 flex-1">
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Chargement…</p>
        ) : items.length === 0 ? (
          <EmptyState icone={Icone} titre={libelleEmptyTitre} message={libelleEmptyMsg} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {items.map((r) => (
              <li
                key={r.id}
                className="px-5 py-3 flex items-center gap-3 hover:bg-slate-50/50 transition-colors"
              >
                <p className="flex-1 text-sm text-slate-900 truncate">{r.libelle}</p>
                {!r.actif && <Badge variante="neutre">Désactivé</Badge>}
                <BoutonsLigne
                  onEditer={() => setEnEdition(r)}
                  onSupprimer={() => {
                    if (confirm(`Désactiver « ${r.libelle} » ?`)) {
                      supp.mutate(r.id);
                    }
                  }}
                />
              </li>
            ))}
          </ul>
        )}
      </CardBody>

      <ModalReferentielEdition
        ouvert={modalCreation || enEdition !== null}
        onFermer={() => {
          setModalCreation(false);
          setEnEdition(null);
        }}
        existant={enEdition}
        titreCreation={libelleModalCreation}
        libelleType={libelleType}
        queryKey={queryKey}
        creer={creer}
        majFn={majFn}
      />
    </Card>
  );
}

interface ModalSimpleProps {
  ouvert: boolean;
  onFermer: () => void;
  existant: Referentiel | null;
  titreCreation: string;
  libelleType: string;
  queryKey: readonly unknown[];
  creer: (libelle: string) => Promise<Referentiel>;
  majFn: (id: number, libelle: string) => Promise<Referentiel>;
}

function ModalReferentielEdition({
  ouvert,
  onFermer,
  existant,
  titreCreation,
  libelleType,
  queryKey,
  creer,
  majFn,
}: ModalSimpleProps) {
  const queryClient = useQueryClient();
  const enEdition = existant !== null;

  const [libelle, setLibelle] = useState(existant?.libelle ?? '');
  const [erreur, setErreur] = useState<string | null>(null);

  if (ouvert && enEdition && existant && libelle !== existant.libelle && erreur === null) {
    setLibelle(existant.libelle);
  }

  function reset() {
    setLibelle('');
    setErreur(null);
    onFermer();
  }

  const creation = useMutation({
    mutationFn: creer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      reset();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  const edition = useMutation({
    mutationFn: (params: { id: number; libelle: string }) => majFn(params.id, params.libelle),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      reset();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    if (enEdition && existant) {
      edition.mutate({ id: existant.id, libelle });
    } else {
      creation.mutate(libelle);
    }
  }

  return (
    <Modal
      ouvert={ouvert}
      onFermer={reset}
      titre={enEdition ? `Modifier « ${existant?.libelle} »` : titreCreation}
      largeur="sm"
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <Input
          label={`Libellé du ${libelleType} *`}
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          autoFocus
          required
        />
        {erreur && <BoiteErreur message={erreur} />}
        <ActionsModal
          onAnnuler={reset}
          chargement={creation.isPending || edition.isPending}
          libelleSubmit={enEdition ? 'Enregistrer' : 'Créer'}
        />
      </form>
    </Modal>
  );
}

// ===========================================================================
// Sous-composants partagés
// ===========================================================================

function BoutonsLigne({
  onEditer,
  onSupprimer,
}: {
  onEditer: () => void;
  onSupprimer: () => void;
}) {
  return (
    <div className="inline-flex gap-1 shrink-0">
      <Button variante="fantome" taille="sm" onClick={onEditer} title="Modifier">
        <Pencil className="h-3.5 w-3.5" />
      </Button>
      <Button variante="fantome" taille="sm" onClick={onSupprimer} title="Désactiver">
        <Ban className={cn('h-3.5 w-3.5 text-red-500')} />
      </Button>
    </div>
  );
}

function BoiteErreur({ message }: { message: string }) {
  return (
    <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
      {message}
    </div>
  );
}

function ActionsModal({
  onAnnuler,
  chargement,
  libelleSubmit,
}: {
  onAnnuler: () => void;
  chargement: boolean;
  libelleSubmit: ReactNode;
}) {
  return (
    <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
      <Button type="button" variante="secondaire" onClick={onAnnuler}>
        Annuler
      </Button>
      <Button type="submit" chargement={chargement}>
        {libelleSubmit}
      </Button>
    </div>
  );
}
