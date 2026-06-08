import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle2,
  FolderOpen,
  MapPin,
  Plus,
  SkipForward,
  Upload,
  X,
} from 'lucide-react';
import { creerDocument } from '@/api/documents';
import { creerCategorie, listerCategories } from '@/api/referentiels';
import type { Categorie } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { Modal } from '@/components/ui/Modal';
import { PageHeader } from '@/components/ui/PageHeader';
import { SelecteurEmplacement } from '@/components/SelecteurEmplacement';
import { extraireMessageErreur } from '@/api/client';

const TAILLE_MAX_MO = 100;

// Extensions acceptées. Doit rester aligné avec le backend `_detecter_mime`.
const EXTENSIONS_ACCEPTEES = new Set([
  'pdf',
  'doc', 'docx',
  'xls', 'xlsx',
  'ppt', 'pptx',
  'odt', 'ods', 'odp',
  'png', 'jpg', 'jpeg', 'gif', 'tiff', 'tif', 'webp', 'bmp',
]);

/**
 * Filtre les fichiers indésirables : système, cachés, verrous Office.
 * Retourne `true` si le fichier doit être conservé.
 */
function fichierAccepte(f: File): boolean {
  const nom = f.name;
  if (nom.startsWith('.')) return false; // .DS_Store, .gitkeep, etc.
  if (nom.startsWith('~$')) return false; // lock Office
  if (nom.toLowerCase() === 'thumbs.db') return false;
  if (nom.toLowerCase() === 'desktop.ini') return false;
  if (f.size === 0) return false;
  if (f.size > TAILLE_MAX_MO * 1024 * 1024) return false;

  const ext = nom.toLowerCase().match(/\.([^.]+)$/)?.[1];
  if (!ext) return false;
  return EXTENSIONS_ACCEPTEES.has(ext);
}

function titreSansExtension(nom: string): string {
  return nom.replace(/\.[^.]+$/, '');
}

type ResultatFichier =
  | { etat: 'ok' }
  | { etat: 'doublon'; existantId?: number }
  | { etat: 'erreur'; message: string };

interface LigneSuivi {
  fichier: File;
  resultat?: ResultatFichier;
}

export default function DocumentsImporter() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [lignes, setLignes] = useState<LigneSuivi[]>([]);
  const [nbIgnores, setNbIgnores] = useState(0);
  const [nomDossier, setNomDossier] = useState<string>('');

  const [categorieId, setCategorieId] = useState<string>('');
  const [emplacement, setEmplacement] = useState<{
    sousDossierId: number;
    code: string;
    libelle: string;
  } | null>(null);

  const [enCours, setEnCours] = useState(false);
  const [indexCourant, setIndexCourant] = useState(0);
  const [termine, setTermine] = useState(false);

  const [modalCategorie, setModalCategorie] = useState(false);
  const [modalEmplacement, setModalEmplacement] = useState(false);

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: listerCategories,
  });

  // Compteurs dérivés (mis à jour à chaque résultat enregistré)
  const compteurs = useMemo(() => {
    let ok = 0, doublons = 0, erreurs = 0;
    for (const l of lignes) {
      if (l.resultat?.etat === 'ok') ok++;
      else if (l.resultat?.etat === 'doublon') doublons++;
      else if (l.resultat?.etat === 'erreur') erreurs++;
    }
    return { ok, doublons, erreurs, total: lignes.length };
  }, [lignes]);

  function reset() {
    setLignes([]);
    setNbIgnores(0);
    setNomDossier('');
    setEnCours(false);
    setIndexCourant(0);
    setTermine(false);
  }

  function onSelectionDossier(e: React.ChangeEvent<HTMLInputElement>) {
    const tous = Array.from(e.target.files ?? []);
    if (tous.length === 0) return;

    const acceptes = tous.filter(fichierAccepte);
    const ignores = tous.length - acceptes.length;

    // Récupère le nom du dossier racine via le webkitRelativePath du premier
    // fichier (ex. "MonDossier/sous/file.pdf" → "MonDossier")
    const premier = tous[0] as File & { webkitRelativePath?: string };
    const chemin = premier.webkitRelativePath ?? '';
    const nom = chemin.split('/')[0] || 'Dossier sélectionné';

    setLignes(acceptes.map((f) => ({ fichier: f })));
    setNbIgnores(ignores);
    setNomDossier(nom);
    setTermine(false);
    setIndexCourant(0);

    // Reset l'input pour permettre de resélectionner le même dossier
    e.target.value = '';
  }

  async function lancerImport() {
    if (!categorieId || lignes.length === 0) return;
    setEnCours(true);
    setTermine(false);

    const catId = Number(categorieId);
    const sousDossierId = emplacement?.sousDossierId ?? null;

    for (let i = 0; i < lignes.length; i++) {
      setIndexCourant(i);
      const ligne = lignes[i];
      try {
        await creerDocument(ligne.fichier, {
          titre: titreSansExtension(ligne.fichier.name),
          description: null,
          resume: null,
          mots_cles: null,
          categorie_id: catId,
          thematique_id: null,
          type_document_id: null,
          date_document: null,
          confidentiel: false,
          sous_dossier_id: sousDossierId,
        });
        setLignes((curr) => {
          const copie = [...curr];
          copie[i] = { ...copie[i], resultat: { etat: 'ok' } };
          return copie;
        });
      } catch (err: unknown) {
        const axiosErr = err as {
          response?: { status?: number; headers?: Record<string, string> };
        };
        if (axiosErr?.response?.status === 409) {
          const existant = axiosErr.response.headers?.['x-document-existant-id'];
          setLignes((curr) => {
            const copie = [...curr];
            copie[i] = {
              ...copie[i],
              resultat: {
                etat: 'doublon',
                existantId: existant ? Number(existant) : undefined,
              },
            };
            return copie;
          });
        } else {
          setLignes((curr) => {
            const copie = [...curr];
            copie[i] = {
              ...copie[i],
              resultat: { etat: 'erreur', message: extraireMessageErreur(err) },
            };
            return copie;
          });
        }
      }
    }

    setEnCours(false);
    setTermine(true);
    queryClient.invalidateQueries({ queryKey: ['documents'] });
  }

  const peutLancer = lignes.length > 0 && categorieId !== '' && !enCours && !termine;
  const progression =
    lignes.length === 0 ? 0 : Math.round(((indexCourant + (enCours ? 0 : 1)) / lignes.length) * 100);

  return (
    <div className="p-6 max-w-4xl space-y-6">
      <PageHeader
        titre="Importer un dossier"
        sousTitre="Sélectionne un dossier — chaque fichier sera créé avec la catégorie choisie. Thématique, type et autres métadonnées resteront vides et pourront être complétés ensuite document par document."
      />

      {/* Étape 1 — choix du dossier */}
      <Card>
        <CardHeader>
          <CardTitle>1. Dossier source</CardTitle>
        </CardHeader>
        <CardBody>
          {lignes.length === 0 ? (
            <label className="flex flex-col items-center justify-center gap-3 cursor-pointer border-2 border-dashed border-slate-300 rounded-xl px-6 py-10 hover:bg-slate-50 transition-colors">
              <FolderOpen className="h-10 w-10 text-brand-600" />
              <div className="text-center">
                <p className="text-sm font-medium text-slate-900">
                  Choisir un dossier
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Tous les sous-dossiers sont parcourus. Formats acceptés : PDF,
                  Word, Excel, PowerPoint, ODT, images.
                </p>
              </div>
              <input
                type="file"
                /* webkitdirectory permet la sélection d'un dossier dans Chrome/Edge/Firefox.
                   React ne connaît pas ces attributs en TS, d'où le @ts-expect-error. */
                /* @ts-expect-error attributs HTML non typés par React */
                webkitdirectory=""
                directory=""
                multiple
                className="hidden"
                onChange={onSelectionDossier}
                disabled={enCours}
              />
            </label>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3 rounded-lg bg-brand-50 border border-brand-200 px-4 py-3">
                <div className="flex items-center gap-3 min-w-0">
                  <FolderOpen className="h-5 w-5 text-brand-700 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {nomDossier}
                    </p>
                    <p className="text-xs text-slate-600">
                      {lignes.length} fichier{lignes.length > 1 ? 's' : ''}{' '}
                      accepté{lignes.length > 1 ? 's' : ''}
                      {nbIgnores > 0 && (
                        <span className="text-slate-500">
                          {' '}
                          · {nbIgnores} ignoré{nbIgnores > 1 ? 's' : ''}
                        </span>
                      )}
                    </p>
                  </div>
                </div>
                {!enCours && !termine && (
                  <button
                    type="button"
                    onClick={reset}
                    className="p-1.5 rounded hover:bg-white text-slate-500 shrink-0"
                    title="Changer de dossier"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Étape 2 — Métadonnées appliquées à tous */}
      {lignes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>2. Métadonnées appliquées à tous les fichiers</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <Select
                  label="Catégorie *"
                  value={categorieId}
                  onChange={(e) => setCategorieId(e.target.value)}
                  required
                  disabled={enCours}
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
                  disabled={enCours}
                >
                  <Plus className="h-4 w-4" /> Nouvelle
                </Button>
              </div>
            </div>

            <div className="border-t pt-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Emplacement physique commun (optionnel)
              </label>
              {emplacement ? (
                <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <MapPin className="h-5 w-5 text-brand-700 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-mono text-slate-700">
                      {emplacement.code}
                    </p>
                    <p className="text-sm text-slate-900 truncate">
                      {emplacement.libelle}
                    </p>
                  </div>
                  {!enCours && (
                    <button
                      type="button"
                      onClick={() => setEmplacement(null)}
                      className="p-1.5 rounded hover:bg-slate-200 text-slate-500"
                      title="Désélectionner"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ) : (
                <Button
                  type="button"
                  variante="secondaire"
                  onClick={() => setModalEmplacement(true)}
                  disabled={enCours}
                >
                  <MapPin className="h-4 w-4" /> Choisir un sous-dossier
                </Button>
              )}
            </div>

            <div className="rounded-lg bg-sky-50 border border-sky-200 px-3 py-2 text-xs text-sky-900">
              Les champs <strong>thématique</strong>, <strong>type de document</strong>,
              <strong> mots-clés</strong>, <strong>résumé</strong> et <strong>date du document</strong>{' '}
              seront laissés vides. Tu pourras les compléter document par document depuis la
              page Documents.
            </div>
          </CardBody>
        </Card>
      )}

      {/* Étape 3 — Liste + actions */}
      {lignes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>
              3. {enCours || termine ? 'Suivi de l\'import' : 'Aperçu'}
            </CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            {/* Barre de progression globale */}
            {(enCours || termine) && (
              <div>
                <div className="flex items-center justify-between text-xs text-slate-600 mb-1.5">
                  <span>
                    {enCours
                      ? `Fichier ${Math.min(indexCourant + 1, lignes.length)} / ${lignes.length}`
                      : 'Terminé'}
                  </span>
                  <span>{progression} %</span>
                </div>
                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500 transition-all"
                    style={{ width: `${progression}%` }}
                  />
                </div>
              </div>
            )}

            {/* Récap si terminé */}
            {termine && (
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
                  <div className="flex items-center gap-2 text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" />
                    <span className="text-xs font-semibold uppercase tracking-wider">
                      Importés
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-emerald-900 mt-1">
                    {compteurs.ok}
                  </p>
                </div>
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                  <div className="flex items-center gap-2 text-amber-700">
                    <SkipForward className="h-4 w-4" />
                    <span className="text-xs font-semibold uppercase tracking-wider">
                      Doublons
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-amber-900 mt-1">
                    {compteurs.doublons}
                  </p>
                </div>
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
                  <div className="flex items-center gap-2 text-red-700">
                    <AlertCircle className="h-4 w-4" />
                    <span className="text-xs font-semibold uppercase tracking-wider">
                      Erreurs
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-red-900 mt-1">
                    {compteurs.erreurs}
                  </p>
                </div>
              </div>
            )}

            {/* Liste détaillée des fichiers */}
            <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-200 divide-y divide-slate-100">
              {lignes.map((l, i) => (
                <LigneFichier
                  key={`${l.fichier.name}-${i}`}
                  ligne={l}
                  enCours={enCours && i === indexCourant}
                />
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Actions */}
      {lignes.length > 0 && (
        <div className="flex justify-end gap-3">
          {!termine ? (
            <>
              <Button
                type="button"
                variante="secondaire"
                onClick={() => navigate('/documents')}
                disabled={enCours}
              >
                Annuler
              </Button>
              <Button
                type="button"
                onClick={lancerImport}
                disabled={!peutLancer}
                chargement={enCours}
              >
                <Upload className="h-4 w-4" />
                {enCours
                  ? `Import en cours…`
                  : `Importer ${lignes.length} fichier${lignes.length > 1 ? 's' : ''}`}
              </Button>
            </>
          ) : (
            <>
              <Button type="button" variante="secondaire" onClick={reset}>
                Importer un autre dossier
              </Button>
              <Button onClick={() => navigate('/documents')}>
                Voir les documents
              </Button>
            </>
          )}
        </div>
      )}

      <NouvelleCategorieModal
        ouvert={modalCategorie}
        onFermer={() => setModalCategorie(false)}
        onCree={(c) => {
          setCategorieId(String(c.id));
          setModalCategorie(false);
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
    </div>
  );
}

// ---------------------------------------------------------------------------

function LigneFichier({ ligne, enCours }: { ligne: LigneSuivi; enCours: boolean }) {
  const { fichier, resultat } = ligne;
  const chemin = (fichier as File & { webkitRelativePath?: string }).webkitRelativePath;

  return (
    <div className="flex items-center gap-3 px-3 py-2 text-sm">
      <div className="flex-1 min-w-0">
        <p className="font-medium text-slate-900 truncate">{fichier.name}</p>
        {chemin && chemin !== fichier.name && (
          <p className="text-xs text-slate-500 truncate font-mono">{chemin}</p>
        )}
      </div>
      <div className="shrink-0">
        {enCours && (
          <Badge couleur="info">
            <div className="h-2 w-2 rounded-full bg-brand-500 animate-pulse" /> En cours
          </Badge>
        )}
        {!enCours && resultat?.etat === 'ok' && (
          <Badge couleur="succes">
            <CheckCircle2 className="h-3.5 w-3.5" /> Importé
          </Badge>
        )}
        {!enCours && resultat?.etat === 'doublon' && (
          <Badge couleur="attention" title="Un document avec le même contenu existe déjà">
            <SkipForward className="h-3.5 w-3.5" /> Doublon
          </Badge>
        )}
        {!enCours && resultat?.etat === 'erreur' && (
          <Badge couleur="erreur" title={resultat.message}>
            <AlertCircle className="h-3.5 w-3.5" /> Erreur
          </Badge>
        )}
        {!resultat && !enCours && (
          <span className="text-xs text-slate-400">En attente</span>
        )}
      </div>
    </div>
  );
}

// Mini-badge local pour la liste — évite de surcharger Badge global avec
// une variante pour chaque palette.
function Badge({
  couleur,
  children,
  title,
}: {
  couleur: 'info' | 'succes' | 'attention' | 'erreur';
  children: React.ReactNode;
  title?: string;
}) {
  const classes = {
    info: 'bg-brand-50 text-brand-700 border-brand-200',
    succes: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    attention: 'bg-amber-50 text-amber-700 border-amber-200',
    erreur: 'bg-red-50 text-red-700 border-red-200',
  }[couleur];
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs font-medium ${classes}`}
    >
      {children}
    </span>
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

  function onSubmit(e: React.FormEvent) {
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
