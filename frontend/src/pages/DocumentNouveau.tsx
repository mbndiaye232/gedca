import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { creerDocument } from '@/api/documents';
import {
  creerCategorie,
  listerCategories,
  listerThematiques,
  listerTypesDocument,
} from '@/api/referentiels';
import type { Categorie } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { Modal } from '@/components/ui/Modal';
import { PageHeader } from '@/components/ui/PageHeader';
import { DropZone } from '@/components/DropZone';
import { extraireMessageErreur } from '@/api/client';

const TAILLE_MAX_MO = 100;

export default function DocumentNouveau() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [fichier, setFichier] = useState<File | null>(null);
  const [titre, setTitre] = useState('');
  const [description, setDescription] = useState('');
  const [resume, setResume] = useState('');
  const [motsCles, setMotsCles] = useState('');
  const [categorieId, setCategorieId] = useState<string>('');
  const [thematiqueId, setThematiqueId] = useState<string>('');
  const [typeDocumentId, setTypeDocumentId] = useState<string>('');
  const [dateDocument, setDateDocument] = useState('');
  const [confidentiel, setConfidentiel] = useState(false);
  const [progression, setProgression] = useState(0);
  const [erreur, setErreur] = useState<string | null>(null);
  const [doublonId, setDoublonId] = useState<number | null>(null);

  const [modalCategorie, setModalCategorie] = useState(false);

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

  // Auto-remplit le titre avec le nom du fichier (sans extension)
  function selectionnerFichier(f: File | null) {
    setFichier(f);
    if (f && !titre) {
      const sansExt = f.name.replace(/\.[^.]+$/, '');
      setTitre(sansExt);
    }
  }

  const upload = useMutation({
    mutationFn: async () => {
      if (!fichier) throw new Error('Aucun fichier sélectionné');
      return creerDocument(
        fichier,
        {
          titre,
          description: description || null,
          resume: resume || null,
          mots_cles: motsCles || null,
          categorie_id: Number(categorieId),
          thematique_id: thematiqueId ? Number(thematiqueId) : null,
          type_document_id: typeDocumentId ? Number(typeDocumentId) : null,
          date_document: dateDocument || null,
          confidentiel,
        },
        (p) => setProgression(p),
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      navigate('/documents');
    },
    onError: (err: unknown) => {
      const message = extraireMessageErreur(err);
      setErreur(message);
      // Détection doublon (HTTP 409 + X-Document-Existant-Id)
      const axiosErr = err as { response?: { status?: number; headers?: Record<string, string> } };
      if (axiosErr?.response?.status === 409) {
        const id = axiosErr.response.headers?.['x-document-existant-id'];
        if (id) setDoublonId(Number(id));
      }
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    setDoublonId(null);
    if (!fichier) {
      setErreur('Sélectionne un fichier à uploader');
      return;
    }
    if (!categorieId) {
      setErreur('La catégorie est obligatoire');
      return;
    }
    if (!titre.trim()) {
      setErreur('Le titre est obligatoire');
      return;
    }
    upload.mutate();
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <PageHeader
        titre="Nouveau document"
        sousTitre="Le fichier sera chiffré au repos et indexé pour la recherche plein texte."
      />

      <form onSubmit={onSubmit} className="space-y-6">
        {/* Fichier */}
        <Card>
          <CardHeader>
            <CardTitle>Fichier</CardTitle>
          </CardHeader>
          <CardBody>
            <DropZone
              fichier={fichier}
              onChange={selectionnerFichier}
              accept=".pdf,.docx,.xlsx,.odt,.png,.jpg,.jpeg,.tiff,.webp,image/*"
              tailleMaxMo={TAILLE_MAX_MO}
              disabled={upload.isPending}
            />
            {upload.isPending && progression > 0 && (
              <div className="mt-4">
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500 transition-all"
                    style={{ width: `${Math.round(progression * 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1 text-right">
                  {Math.round(progression * 100)} %
                </p>
              </div>
            )}
          </CardBody>
        </Card>

        {/* Métadonnées */}
        <Card>
          <CardHeader>
            <CardTitle>Métadonnées</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            <Input
              label="Titre *"
              value={titre}
              onChange={(e) => setTitre(e.target.value)}
              required
              maxLength={512}
            />

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <Select
                  label="Catégorie *"
                  value={categorieId}
                  onChange={(e) => setCategorieId(e.target.value)}
                  required
                >
                  <option value="">— choisir —</option>
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

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
          </CardBody>
        </Card>

        {/* Erreurs */}
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
            {doublonId !== null && (
              <p className="mt-1">
                <a
                  href={`/documents`}
                  className="underline font-medium"
                >
                  Voir le document existant (#{doublonId})
                </a>
              </p>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variante="secondaire"
            onClick={() => navigate('/documents')}
            disabled={upload.isPending}
          >
            Annuler
          </Button>
          <Button type="submit" chargement={upload.isPending} disabled={!fichier}>
            Téléverser
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
    </div>
  );
}

// ---------------------------------------------------------------------------

interface ModalCatProps {
  ouvert: boolean;
  onFermer: () => void;
  onCree: (c: Categorie) => void;
}

function NouvelleCategorieModal({ ouvert, onFermer, onCree }: ModalCatProps) {
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
