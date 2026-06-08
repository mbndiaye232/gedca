import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MapPin, Plus, X } from 'lucide-react';
import { majDocument } from '@/api/documents';
import {
  creerCategorie,
  creerThematique,
  creerTypeDocument,
  listerCategories,
  listerThematiques,
  listerTypesDocument,
} from '@/api/referentiels';
import type { Categorie, Document, Referentiel } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { SelecteurEmplacement } from '@/components/SelecteurEmplacement';
import { extraireMessageErreur } from '@/api/client';

interface Props {
  document: Document;
  onFermer: () => void;
}

/**
 * Modal d'édition des métadonnées d'un document existant.
 *
 * Le fichier (binaire) n'est pas modifiable — pour le remplacer il faut
 * supprimer + recréer un document. Tous les autres champs sont éditables :
 * titre, classement (catégorie/thématique/type), date, mots-clés, résumé,
 * description, confidentialité, emplacement physique.
 *
 * Le composant est monté à la demande avec key={doc.id} (pattern habituel
 * des autres modaux du projet), donc l'état initial est dérivé du `document`
 * passé en prop sans `useEffect` de resync.
 */
export function ModalEditDocument({ document: doc, onFermer }: Props) {
  const queryClient = useQueryClient();

  const [titre, setTitre] = useState(doc.titre);
  const [description, setDescription] = useState(doc.description ?? '');
  const [resume, setResume] = useState(doc.resume ?? '');
  const [motsCles, setMotsCles] = useState(doc.mots_cles ?? '');
  const [categorieId, setCategorieId] = useState<string>(
    doc.categorie_id ? String(doc.categorie_id) : '',
  );
  const [thematiqueId, setThematiqueId] = useState<string>(
    doc.thematique_id ? String(doc.thematique_id) : '',
  );
  const [typeDocumentId, setTypeDocumentId] = useState<string>(
    doc.type_document_id ? String(doc.type_document_id) : '',
  );
  const [dateDocument, setDateDocument] = useState(doc.date_document ?? '');
  const [confidentiel, setConfidentiel] = useState(doc.confidentiel);
  const [emplacement, setEmplacement] = useState<{
    sousDossierId: number;
    code: string;
    libelle: string;
  } | null>(
    doc.emplacement
      ? {
          sousDossierId: doc.emplacement.sous_dossier_id,
          code: doc.emplacement.code_complet,
          libelle: doc.emplacement.sous_dossier.libelle,
        }
      : null,
  );

  const [erreur, setErreur] = useState<string | null>(null);
  const [modalCategorie, setModalCategorie] = useState(false);
  const [modalThematique, setModalThematique] = useState(false);
  const [modalTypeDocument, setModalTypeDocument] = useState(false);
  const [modalEmplacement, setModalEmplacement] = useState(false);

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: listerCategories,
  });
  const { data: thematiques = [] } = useQuery({
    queryKey: ['thematiques'],
    queryFn: listerThematiques,
  });
  const { data: types = [] } = useQuery({
    queryKey: ['types-document'],
    queryFn: listerTypesDocument,
  });

  const mutation = useMutation({
    mutationFn: () =>
      majDocument(doc.id, {
        titre,
        description: description || null,
        resume: resume || null,
        mots_cles: motsCles || null,
        categorie_id: categorieId ? Number(categorieId) : null,
        thematique_id: thematiqueId ? Number(thematiqueId) : null,
        type_document_id: typeDocumentId ? Number(typeDocumentId) : null,
        date_document: dateDocument || null,
        confidentiel,
        sous_dossier_id: emplacement?.sousDossierId ?? null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      onFermer();
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    if (!titre.trim()) {
      setErreur('Le titre est obligatoire');
      return;
    }
    mutation.mutate();
  }

  return (
    <Modal
      ouvert
      onFermer={onFermer}
      titre={`Modifier « ${doc.titre} »`}
      largeur="lg"
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <Input
          label="Titre *"
          value={titre}
          onChange={(e) => setTitre(e.target.value)}
          required
          maxLength={512}
        />

        {/* Catégorie + bouton "nouvelle" */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-2">
            <Select
              label="Catégorie"
              value={categorieId}
              onChange={(e) => setCategorieId(e.target.value)}
            >
              <option value="">— aucune —</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.libelle}</option>
              ))}
            </Select>
          </div>
          <div className="flex items-end">
            <Button
              type="button"
              variante="secondaire"
              onClick={() => setModalCategorie(true)}
              className="w-full"
            >
              <Plus className="h-4 w-4" /> Nouvelle
            </Button>
          </div>
        </div>

        {/* Thématique + Type avec création inline */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <Select
                label="Thématique"
                value={thematiqueId}
                onChange={(e) => setThematiqueId(e.target.value)}
              >
                <option value="">— aucune —</option>
                {thematiques.map((t) => (
                  <option key={t.id} value={t.id}>{t.libelle}</option>
                ))}
              </Select>
            </div>
            <Button
              type="button"
              variante="secondaire"
              onClick={() => setModalThematique(true)}
              title="Nouvelle thématique"
              className="shrink-0"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <Select
                label="Type de document"
                value={typeDocumentId}
                onChange={(e) => setTypeDocumentId(e.target.value)}
              >
                <option value="">— aucun —</option>
                {types.map((t) => (
                  <option key={t.id} value={t.id}>{t.libelle}</option>
                ))}
              </Select>
            </div>
            <Button
              type="button"
              variante="secondaire"
              onClick={() => setModalTypeDocument(true)}
              title="Nouveau type de document"
              className="shrink-0"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <Input
          label="Date du document"
          type="date"
          value={dateDocument}
          onChange={(e) => setDateDocument(e.target.value)}
        />

        <Input
          label="Mots-clés"
          value={motsCles}
          onChange={(e) => setMotsCles(e.target.value)}
          placeholder="Séparés par des espaces ou virgules"
        />

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Résumé
          </label>
          <textarea
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            rows={3}
            value={resume}
            onChange={(e) => setResume(e.target.value)}
            placeholder="Description courte pour différencier ce document"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description longue
          </label>
          <textarea
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={confidentiel}
            onChange={(e) => setConfidentiel(e.target.checked)}
            className="rounded border-gray-300"
          />
          Confidentiel — restreint aux archivistes et superviseurs
        </label>

        {/* Emplacement physique */}
        <div className="border-t pt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Emplacement physique (optionnel)
          </label>
          {emplacement ? (
            <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
              <MapPin className="h-5 w-5 text-brand-700 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-mono text-gray-700">{emplacement.code}</p>
                <p className="text-sm text-gray-900 truncate">{emplacement.libelle}</p>
              </div>
              <button
                type="button"
                onClick={() => setEmplacement(null)}
                className="p-1.5 rounded hover:bg-gray-200 text-gray-500"
                title="Désélectionner"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <Button
              type="button"
              variante="secondaire"
              onClick={() => setModalEmplacement(true)}
            >
              <MapPin className="h-4 w-4" /> Choisir un sous-dossier physique
            </Button>
          )}
        </div>

        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
          <Button
            type="button"
            variante="secondaire"
            onClick={onFermer}
            disabled={mutation.isPending}
          >
            Annuler
          </Button>
          <Button type="submit" chargement={mutation.isPending}>
            Enregistrer
          </Button>
        </div>
      </form>

      <NouvelleCategorieModal
        ouvert={modalCategorie}
        onFermer={() => setModalCategorie(false)}
        onCree={(c) => {
          setCategorieId(String(c.id));
          setModalCategorie(false);
        }}
      />
      <ModalReferentielSimple
        ouvert={modalThematique}
        onFermer={() => setModalThematique(false)}
        titre="Nouvelle thématique"
        queryKey={['thematiques']}
        mutationFn={creerThematique}
        onCree={(r) => {
          setThematiqueId(String(r.id));
          setModalThematique(false);
        }}
      />
      <ModalReferentielSimple
        ouvert={modalTypeDocument}
        onFermer={() => setModalTypeDocument(false)}
        titre="Nouveau type de document"
        queryKey={['types-document']}
        mutationFn={creerTypeDocument}
        onCree={(r) => {
          setTypeDocumentId(String(r.id));
          setModalTypeDocument(false);
        }}
      />
      <SelecteurEmplacement
        ouvert={modalEmplacement}
        onFermer={() => setModalEmplacement(false)}
        onSelectionner={(sousDossierId, code, libelle) => {
          setEmplacement({ sousDossierId, code, libelle });
          setModalEmplacement(false);
        }}
      />
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Sous-modaux locaux — identiques à ceux de DocumentNouveau, recopiés pour
// rester autonomes. À factoriser si on en a un 3e usage (YAGNI pour l'instant).
// ---------------------------------------------------------------------------

function NouvelleCategorieModal({
  ouvert,
  onFermer,
  onCree,
}: {
  ouvert: boolean;
  onFermer: () => void;
  onCree: (c: Categorie) => void;
}) {
  const queryClient = useQueryClient();
  const [libelle, setLibelle] = useState('');
  const [description, setDescription] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);

  const creation = useMutation({
    mutationFn: creerCategorie,
    onSuccess: (cat) => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      onCree(cat);
      setLibelle('');
      setDescription('');
      setErreur(null);
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    creation.mutate({ libelle, description: description || null });
  }

  return (
    <Modal ouvert={ouvert} onFermer={onFermer} titre="Nouvelle catégorie" largeur="sm">
      <form onSubmit={onSubmit} className="space-y-4">
        <Input
          label="Libellé *"
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          required
          autoFocus
        />
        <Input
          label="Description (optionnel)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button type="submit" chargement={creation.isPending}>
            Créer
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ModalReferentielSimple({
  ouvert,
  onFermer,
  titre,
  queryKey,
  mutationFn,
  onCree,
}: {
  ouvert: boolean;
  onFermer: () => void;
  titre: string;
  queryKey: readonly unknown[];
  mutationFn: (libelle: string) => Promise<Referentiel>;
  onCree: (r: Referentiel) => void;
}) {
  const queryClient = useQueryClient();
  const [libelle, setLibelle] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);

  const creation = useMutation({
    mutationFn,
    onSuccess: (r) => {
      queryClient.invalidateQueries({ queryKey });
      onCree(r);
      setLibelle('');
      setErreur(null);
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    creation.mutate(libelle);
  }

  return (
    <Modal ouvert={ouvert} onFermer={onFermer} titre={titre} largeur="sm">
      <form onSubmit={onSubmit} className="space-y-4">
        <Input
          label="Libellé *"
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          required
          autoFocus
        />
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button type="submit" chargement={creation.isPending}>
            Créer
          </Button>
        </div>
      </form>
    </Modal>
  );
}
