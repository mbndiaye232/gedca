import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowDownLeft,
  ArrowUpRight,
  Calendar,
  CheckCircle2,
  Copy as CopyIcon,
  Eye,
  FileText,
  History,
  MapPin,
  Mail,
  Paperclip,
  Reply,
  RefreshCw,
  Send,
  StickyNote,
  User,
  Users,
} from 'lucide-react';
import {
  ajouterNote,
  ajouterPiece,
  envoyer,
  faireUneCopie,
  imputer,
  lireCourrier,
  repondre,
} from '@/api/courriers';
import { listerAgents } from '@/api/agents';
import { listerCategories } from '@/api/referentiels';
import { lireDocument, telechargerContenu } from '@/api/documents';
import type {
  Agent,
  Courrier,
  CourrierDetail,
  Document,
  HistoriqueCourrier,
  RepondreBody,
  SensCourrier,
} from '@/api/types';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { DropZone } from '@/components/DropZone';
import { Visionneuse } from '@/components/Visionneuse';
import { extraireMessageErreur } from '@/api/client';
import { formatDate, formatDateTime, cn } from '@/lib/utils';
import { useAuth } from '@/auth/useAuth';

interface Props {
  ouvert: boolean;
  courrierId: number;
  onFermer: () => void;
}

const TONS_SENS: Record<SensCourrier, string> = {
  entrant: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  sortant: 'bg-sky-50 text-sky-700 ring-sky-200',
  interne: 'bg-violet-50 text-violet-700 ring-violet-200',
};

export function ModalTraiter({ ouvert, courrierId, onFermer }: Props) {
  const { agent: agentCourant } = useAuth();
  const queryClient = useQueryClient();

  const { data: courrier, isLoading, error } = useQuery({
    queryKey: ['courriers', 'detail', courrierId],
    queryFn: () => lireCourrier(courrierId),
    enabled: ouvert,
    retry: false,
  });

  const [actionEnCours, setActionEnCours] = useState<
    'copie' | 'imputer' | 'note' | 'document' | 'repondre' | null
  >(null);
  const [docPourVisionneuse, setDocPourVisionneuse] = useState<Document | null>(null);

  if (!agentCourant) return null;

  const traite = courrier?.statut.code === 'traite';
  const proprietaire = courrier?.agent_proprietaire_id === agentCourant.id;
  const peutTraiter = !traite && courrier !== undefined;

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['courriers'] });
  }

  async function onPreviewDocument(documentId: number) {
    try {
      const doc = await lireDocument(documentId);
      setDocPourVisionneuse(doc);
    } catch (e) {
      alert(extraireMessageErreur(e));
    }
  }

  return (
    <Modal
      ouvert={ouvert}
      onFermer={onFermer}
      titre={courrier ? `Courrier ${courrier.numero_enregistrement}` : 'Courrier'}
      largeur="xl"
    >
      {isLoading ? (
        <p className="text-sm text-slate-500 py-8 text-center">Chargement…</p>
      ) : error ? (
        <div className="py-8 px-4">
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800">
            <p className="font-medium mb-1">Impossible d'afficher ce courrier</p>
            <p className="text-xs">{extraireMessageErreur(error, "Accès refusé ou courrier introuvable.")}</p>
            <p className="text-xs mt-2 text-red-600">
              Tu ne fais peut-être plus partie des agents qui voient ce courrier
              (par exemple après une imputation à un autre agent).
            </p>
          </div>
          <div className="flex justify-end mt-4">
            <Button variante="secondaire" onClick={onFermer}>
              Fermer
            </Button>
          </div>
        </div>
      ) : !courrier ? (
        <p className="text-sm text-slate-500 py-8 text-center">Chargement…</p>
      ) : (
        <div className="space-y-5">
          <EnTeteCourrier courrier={courrier} />

          {/* Pièces */}
          <SectionPieces
            courrier={courrier}
            onOuvrirPiece={onPreviewDocument}
            peutAjouter={peutTraiter}
            onAjouterPiece={() => setActionEnCours('document')}
          />

          {/* Actions */}
          {peutTraiter && (
            <div className="flex flex-wrap gap-2 pt-3 border-t border-slate-100">
              <Button variante="secondaire" taille="sm" onClick={() => setActionEnCours('copie')}>
                <CopyIcon className="h-4 w-4" /> Faire une copie
              </Button>
              {proprietaire && (
                <Button variante="secondaire" taille="sm" onClick={() => setActionEnCours('imputer')}>
                  <Users className="h-4 w-4" /> Imputer
                </Button>
              )}
              <Button variante="secondaire" taille="sm" onClick={() => setActionEnCours('repondre')}>
                <Reply className="h-4 w-4" /> Répondre
              </Button>
              <Button variante="secondaire" taille="sm" onClick={() => setActionEnCours('note')}>
                <StickyNote className="h-4 w-4" /> Ajouter une note
              </Button>
              {proprietaire && (
                <Button taille="sm" onClick={() => doEnvoyer(courrier.id, invalidate, onFermer)}>
                  <Send className="h-4 w-4" /> Envoyer (clôturer)
                </Button>
              )}
            </div>
          )}

          {/* Notes */}
          <CollapsibleSection
            titre={`Notes (${courrier.notes.length})`}
            icone={StickyNote}
            defaultOpen={courrier.notes.length > 0}
          >
            {courrier.notes.length === 0 ? (
              <p className="text-xs text-slate-500 italic">Aucune note pour l'instant.</p>
            ) : (
              <ul className="space-y-2">
                {courrier.notes.map((n) => (
                  <li
                    key={n.id}
                    className="rounded-lg bg-amber-50 border border-amber-100 px-3 py-2"
                  >
                    <p className="text-sm text-slate-900 whitespace-pre-wrap">{n.contenu}</p>
                    <p className="text-[10px] uppercase tracking-wider text-slate-500 mt-1">
                      {formatDateTime(n.created_at)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CollapsibleSection>

          {/* Historique */}
          <CollapsibleSection
            titre={`Historique (${courrier.historique.length})`}
            icone={History}
          >
            <ul className="space-y-2">
              {courrier.historique.map((h) => (
                <LigneHistorique key={h.id} entree={h} />
              ))}
            </ul>
          </CollapsibleSection>

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <Button variante="secondaire" onClick={onFermer}>
              Fermer
            </Button>
          </div>
        </div>
      )}

      {/* Sous-modals d'action */}
      {courrier && actionEnCours === 'copie' && (
        <ModalCopie
          courrier={courrier}
          onFermer={() => setActionEnCours(null)}
          onSucces={() => {
            setActionEnCours(null);
            invalidate();
          }}
        />
      )}
      {courrier && actionEnCours === 'imputer' && (
        <ModalImputer
          courrier={courrier}
          onFermer={() => setActionEnCours(null)}
          onSucces={() => {
            setActionEnCours(null);
            invalidate();
          }}
        />
      )}
      {courrier && actionEnCours === 'note' && (
        <ModalNote
          courrierId={courrier.id}
          onFermer={() => setActionEnCours(null)}
          onSucces={() => {
            setActionEnCours(null);
            invalidate();
          }}
        />
      )}
      {courrier && actionEnCours === 'document' && (
        <ModalAjouterPiece
          courrierId={courrier.id}
          onFermer={() => setActionEnCours(null)}
          onSucces={() => {
            setActionEnCours(null);
            invalidate();
          }}
        />
      )}
      {courrier && actionEnCours === 'repondre' && (
        <ModalRepondre
          courrier={courrier}
          onFermer={() => setActionEnCours(null)}
          onSucces={() => {
            setActionEnCours(null);
            invalidate();
            onFermer();
          }}
        />
      )}

      <Visionneuse
        ouvert={docPourVisionneuse !== null}
        document={docPourVisionneuse}
        onFermer={() => setDocPourVisionneuse(null)}
      />
    </Modal>
  );
}

async function doEnvoyer(id: number, onOk: () => void, onFermer: () => void) {
  if (!confirm("Clôturer ce courrier ? Il passera à l'état « Traité ».")) return;
  try {
    await envoyer(id);
    onOk();
    onFermer();
  } catch (e) {
    alert(extraireMessageErreur(e));
  }
}

// ---------------------------------------------------------------------------
// Sous-composants présentation
// ---------------------------------------------------------------------------

function EnTeteCourrier({ courrier }: { courrier: CourrierDetail }) {
  const SensIcone =
    courrier.sens === 'entrant'
      ? ArrowDownLeft
      : courrier.sens === 'sortant'
      ? ArrowUpRight
      : RefreshCw;

  function correspondantText(): string {
    if (!courrier.correspondant) return '—';
    if (courrier.correspondant.raison_sociale) return courrier.correspondant.raison_sociale;
    return `${courrier.correspondant.prenom ?? ''} ${courrier.correspondant.nom ?? ''}`.trim();
  }

  return (
    <div className="rounded-2xl bg-gradient-to-br from-slate-50 to-white border border-slate-200 p-4 space-y-3">
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'inline-flex h-10 w-10 items-center justify-center rounded-xl ring-1 ring-inset shrink-0',
            TONS_SENS[courrier.sens],
          )}
        >
          <SensIcone className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">
            {courrier.sens} · {courrier.numero_enregistrement}
          </p>
          <h3 className="text-base font-semibold text-slate-900 tracking-tight mt-0.5">
            {courrier.objet}
          </h3>
        </div>
        <Badge variante="info" pastille>
          {courrier.statut.libelle}
        </Badge>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <Info icone={User} libelle="Correspondant" valeur={correspondantText()} />
        <Info icone={Calendar} libelle="Date courrier" valeur={formatDate(courrier.date_courrier)} />
        <Info icone={Calendar} libelle="Date limite" valeur={formatDate(courrier.date_limite)} />
        <Info icone={Mail} libelle="Référence" valeur={courrier.ref_externe ?? '—'} />
      </div>

      {courrier.mots_cles && (
        <div className="text-xs text-slate-500">
          <span className="font-medium text-slate-700">Mots-clés :</span> {courrier.mots_cles}
        </div>
      )}
      {courrier.observations && (
        <div className="text-xs text-slate-500">
          <span className="font-medium text-slate-700">Observations :</span> {courrier.observations}
        </div>
      )}
    </div>
  );
}

function Info({
  icone: Icone,
  libelle,
  valeur,
}: {
  icone: typeof User;
  libelle: string;
  valeur: string;
}) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-slate-400 flex items-center gap-1">
        <Icone className="h-3 w-3" /> {libelle}
      </p>
      <p className="text-slate-900 font-medium mt-0.5 truncate" title={valeur}>
        {valeur}
      </p>
    </div>
  );
}

function SectionPieces({
  courrier,
  onOuvrirPiece,
  peutAjouter,
  onAjouterPiece,
}: {
  courrier: CourrierDetail;
  onOuvrirPiece: (docId: number) => void;
  peutAjouter: boolean;
  onAjouterPiece: () => void;
}) {
  const pieces = [
    { id: courrier.document_principal_id, principal: true },
    ...courrier.pieces_additionnelles.map((id) => ({ id, principal: false })),
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
          Pièces ({pieces.length})
        </h4>
        {peutAjouter && (
          <Button variante="fantome" taille="sm" onClick={onAjouterPiece}>
            <Paperclip className="h-3.5 w-3.5" /> Ajouter
          </Button>
        )}
      </div>
      <ul className="space-y-1.5">
        {pieces.map((p) => (
          <li
            key={p.id}
            className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2"
          >
            <FileText className="h-4 w-4 text-brand-600 shrink-0" />
            <div className="flex-1 text-sm text-slate-900">
              Document #{p.id}
              {p.principal && (
                <Badge className="ml-2" variante="violet">
                  Principal
                </Badge>
              )}
            </div>
            <Button variante="fantome" taille="sm" onClick={() => onOuvrirPiece(p.id)}>
              <Eye className="h-4 w-4" />
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CollapsibleSection({
  titre,
  icone: Icone,
  defaultOpen = false,
  children,
}: {
  titre: string;
  icone: typeof StickyNote;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [ouvert, setOuvert] = useState(defaultOpen);
  return (
    <div className="border-t border-slate-100 pt-3">
      <button
        type="button"
        onClick={() => setOuvert((o) => !o)}
        className="flex items-center justify-between w-full text-left mb-2"
      >
        <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-600">
          <Icone className="h-3.5 w-3.5" /> {titre}
        </span>
        <span className="text-xs text-slate-400">{ouvert ? '−' : '+'}</span>
      </button>
      {ouvert && <div>{children}</div>}
    </div>
  );
}

function LigneHistorique({ entree }: { entree: HistoriqueCourrier }) {
  return (
    <li className="flex items-start gap-2 text-xs">
      <div className="h-1.5 w-1.5 rounded-full bg-brand-600 mt-1.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-slate-900 font-medium">{entree.action.libelle}</p>
        <p className="text-slate-500">
          {entree.agent_id ? `Agent #${entree.agent_id} · ` : ''}
          {formatDateTime(entree.ts)}
        </p>
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Sous-modals d'action
// ---------------------------------------------------------------------------

function ModalCopie({
  courrier,
  onFermer,
  onSucces,
}: {
  courrier: CourrierDetail;
  onFermer: () => void;
  onSucces: () => void;
}) {
  const { data: agents = [] } = useQuery({ queryKey: ['agents'], queryFn: listerAgents });
  const [selectionnes, setSelectionnes] = useState<number[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);

  // Exclure le propriétaire et les déjà-en-copie
  const idsExclus = new Set([
    courrier.agent_proprietaire_id,
    ...courrier.copies.map((c) => c.id),
  ]);
  const disponibles = agents.filter((a) => !idsExclus.has(a.id) && a.actif);

  const mutation = useMutation({
    mutationFn: () => faireUneCopie(courrier.id, selectionnes),
    onSuccess: onSucces,
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function toggle(id: number) {
    setSelectionnes((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  return (
    <Modal ouvert onFermer={onFermer} titre="Faire une copie" largeur="sm">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Sélectionne les agents qui recevront ce courrier en copie.
        </p>
        <div className="max-h-64 overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100">
          {disponibles.length === 0 ? (
            <p className="p-4 text-center text-xs text-slate-500">
              Aucun agent disponible (tous sont déjà en copie ou propriétaire).
            </p>
          ) : (
            disponibles.map((a) => (
              <label
                key={a.id}
                className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-slate-50"
              >
                <input
                  type="checkbox"
                  checked={selectionnes.includes(a.id)}
                  onChange={() => toggle(a.id)}
                  className="rounded border-slate-300"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-900 truncate">
                    {a.prenom} {a.nom}
                  </p>
                  <p className="text-xs text-slate-500 truncate">{a.email}</p>
                </div>
              </label>
            ))
          )}
        </div>
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button
            disabled={selectionnes.length === 0}
            chargement={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Valider ({selectionnes.length})
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function ModalImputer({
  courrier,
  onFermer,
  onSucces,
}: {
  courrier: CourrierDetail;
  onFermer: () => void;
  onSucces: () => void;
}) {
  const { data: agents = [] } = useQuery({ queryKey: ['agents'], queryFn: listerAgents });
  const [agentId, setAgentId] = useState<string>('');
  const [instruction, setInstruction] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);

  const disponibles = agents.filter(
    (a) => a.id !== courrier.agent_proprietaire_id && a.actif,
  );

  const mutation = useMutation({
    mutationFn: () => imputer(courrier.id, Number(agentId), instruction || undefined),
    onSuccess: onSucces,
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  return (
    <Modal ouvert onFermer={onFermer} titre="Imputer le courrier" largeur="sm">
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          setErreur(null);
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <p className="text-sm text-slate-600">
          Le destinataire deviendra propriétaire du courrier. Tu passeras en copie.
        </p>
        <Select
          label="Agent destinataire *"
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
          required
        >
          <option value="">— choisir —</option>
          {disponibles.map((a) => (
            <option key={a.id} value={a.id}>
              {a.prenom} {a.nom}
            </option>
          ))}
        </Select>
        <Input
          label="Instruction (optionnelle)"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
        />
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button type="submit" disabled={!agentId} chargement={mutation.isPending}>
            Imputer
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ModalNote({
  courrierId,
  onFermer,
  onSucces,
}: {
  courrierId: number;
  onFermer: () => void;
  onSucces: () => void;
}) {
  const [contenu, setContenu] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => ajouterNote(courrierId, contenu),
    onSuccess: onSucces,
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  return (
    <Modal ouvert onFermer={onFermer} titre="Ajouter une note" largeur="sm">
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          setErreur(null);
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <textarea
          autoFocus
          className="block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          rows={5}
          value={contenu}
          onChange={(e) => setContenu(e.target.value)}
          required
          maxLength={1000}
          placeholder="Post-it visible par tous les agents qui voient ce courrier."
        />
        <p className="text-xs text-slate-500 text-right">{contenu.length} / 1000</p>
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button type="submit" disabled={!contenu.trim()} chargement={mutation.isPending}>
            Ajouter
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ModalAjouterPiece({
  courrierId,
  onFermer,
  onSucces,
}: {
  courrierId: number;
  onFermer: () => void;
  onSucces: () => void;
}) {
  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: listerCategories });
  const [fichier, setFichier] = useState<File | null>(null);
  const [titre, setTitre] = useState('');
  const [categorieId, setCategorieId] = useState<string>('');
  const [erreur, setErreur] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      ajouterPiece(courrierId, fichier!, titre, Number(categorieId)),
    onSuccess: onSucces,
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function selFichier(f: File | null) {
    setFichier(f);
    if (f && !titre) setTitre(f.name.replace(/\.[^.]+$/, ''));
  }

  return (
    <Modal ouvert onFermer={onFermer} titre="Ajouter une pièce" largeur="sm">
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          setErreur(null);
          if (!fichier || !titre || !categorieId) return;
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <DropZone fichier={fichier} onChange={selFichier} tailleMaxMo={100} />
        <Input
          label="Titre *"
          value={titre}
          onChange={(e) => setTitre(e.target.value)}
          required
        />
        <Select
          label="Catégorie *"
          value={categorieId}
          onChange={(e) => setCategorieId(e.target.value)}
          required
        >
          <option value="">— choisir —</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.libelle}
            </option>
          ))}
        </Select>
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button
            type="submit"
            disabled={!fichier || !titre || !categorieId}
            chargement={mutation.isPending}
          >
            Ajouter
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ModalRepondre({
  courrier,
  onFermer,
  onSucces,
}: {
  courrier: CourrierDetail;
  onFermer: () => void;
  onSucces: () => void;
}) {
  const { data: agents = [] } = useQuery({ queryKey: ['agents'], queryFn: listerAgents });
  const { data: categories = [] } = useQuery({ queryKey: ['categories'], queryFn: listerCategories });

  const [fichier, setFichier] = useState<File | null>(null);
  const [objet, setObjet] = useState(`Rép : ${courrier.objet}`);
  const [agentId, setAgentId] = useState<string>('');
  const [categorieId, setCategorieId] = useState<string>(
    courrier.categorie_id ? String(courrier.categorie_id) : '',
  );
  const [erreur, setErreur] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => {
      const body: RepondreBody = {
        objet,
        agent_destinataire_id: Number(agentId),
        document_titre: fichier?.name.replace(/\.[^.]+$/, '') || 'Réponse',
        document_categorie_id: Number(categorieId),
      };
      return repondre(courrier.id, fichier!, body);
    },
    onSuccess: onSucces,
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  return (
    <Modal ouvert onFermer={onFermer} titre="Répondre" largeur="md">
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          setErreur(null);
          if (!fichier || !agentId || !categorieId) return;
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <div className="rounded-lg bg-sky-50 border border-sky-200 px-3 py-2 text-xs text-sky-900">
          <strong>Réponse</strong> = nouveau courrier sortant lié à l'origine. Le document original
          reste attaché au courrier d'origine — tu joins ci-dessous{' '}
          <strong>le document de ta réponse</strong>.
        </div>
        <Input label="Objet *" value={objet} onChange={(e) => setObjet(e.target.value)} required />
        <Select
          label="Agent qui traitera la réponse *"
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
          required
        >
          <option value="">— choisir —</option>
          {agents.filter((a) => a.actif).map((a) => (
            <option key={a.id} value={a.id}>
              {a.prenom} {a.nom}
            </option>
          ))}
        </Select>
        <Select
          label="Catégorie *"
          value={categorieId}
          onChange={(e) => setCategorieId(e.target.value)}
          required
        >
          <option value="">— choisir —</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.libelle}
            </option>
          ))}
        </Select>
        <div>
          <label className="block text-xs font-medium text-slate-700 tracking-wide mb-1.5">
            Document de la réponse *
          </label>
          <DropZone
            fichier={fichier}
            onChange={setFichier}
            tailleMaxMo={100}
            invite="Glisse ici le PDF / Word de ta réponse"
          />
        </div>
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button
            type="submit"
            disabled={!fichier || !agentId || !categorieId}
            chargement={mutation.isPending}
          >
            Envoyer la réponse
          </Button>
        </div>
      </form>
    </Modal>
  );
}
