import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { creerCourrier } from '@/api/courriers';
import { listerAgentsDestinataires } from '@/api/agents';
import { listerDepartements } from '@/api/departements';
import { listerCategories, creerCategorie } from '@/api/referentiels';
import { creerCorrespondant, listerCorrespondants } from '@/api/correspondants';
import type {
  Correspondant,
  CorrespondantCreation,
  CourrierCreationBody,
  SensCourrier,
} from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { DropZone } from '@/components/DropZone';
import { PageHeader } from '@/components/ui/PageHeader';
import { extraireMessageErreur } from '@/api/client';
import { useAuth } from '@/auth/useAuth';
import { cn } from '@/lib/utils';

const SENS_OPTIONS: { code: SensCourrier; libelle: string; description: string }[] = [
  { code: 'entrant', libelle: 'Entrant', description: 'Courrier reçu d\'un correspondant externe' },
  { code: 'sortant', libelle: 'Sortant', description: 'Courrier envoyé à un correspondant externe' },
  { code: 'interne', libelle: 'Interne', description: 'Échange entre agents de l\'organisation' },
];

const TAILLE_MAX_MO = 100;

export default function CourrierNouveau() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { agent: agentCourant } = useAuth();

  const [sens, setSens] = useState<SensCourrier>('entrant');
  const [refExterne, setRefExterne] = useState('');
  const [objet, setObjet] = useState('');
  const [motsCles, setMotsCles] = useState('');
  const [observations, setObservations] = useState('');
  const [categorieId, setCategorieId] = useState<string>('');
  const [dateCourrier, setDateCourrier] = useState('');
  const [dateArrivee, setDateArrivee] = useState('');
  const [dateLimite, setDateLimite] = useState('');
  const [correspondantId, setCorrespondantId] = useState<string>('');
  const [departementId, setDepartementId] = useState<string>('');
  const [agentDestinataireId, setAgentDestinataireId] = useState<string>(
    agentCourant ? String(agentCourant.id) : '',
  );

  const [fichier, setFichier] = useState<File | null>(null);
  const [documentTitre, setDocumentTitre] = useState('');
  const [documentCategorieId, setDocumentCategorieId] = useState<string>('');

  // PRD-06B : si coché, le courrier arrive en statut a_faire_valider
  // chez son destinataire (au lieu de a_traiter). Le destinataire devra
  // demander la validation à un agent avant de pouvoir envoyer.
  const [aFaireValider, setAFaireValider] = useState(false);

  const [progression, setProgression] = useState(0);
  const [erreur, setErreur] = useState<string | null>(null);

  const [modalCorrespondant, setModalCorrespondant] = useState(false);
  const [modalCategorieDoc, setModalCategorieDoc] = useState(false);

  const { data: agents = [] } = useQuery({
    queryKey: ['agents', 'destinataires'],
    queryFn: listerAgentsDestinataires,
  });
  const { data: departements = [] } = useQuery({
    queryKey: ['departements'],
    queryFn: listerDepartements,
  });
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: listerCategories,
  });
  const { data: correspondants = [] } = useQuery({
    queryKey: ['correspondants', sens],
    queryFn: () => listerCorrespondants(),
    enabled: sens !== 'interne',
  });

  // Le backend ne renvoie déjà que les agents actifs ; on garde juste la
  // cascade département → liste filtrée.
  const agentsFiltres = departementId
    ? agents.filter((a) => a.departement_id === Number(departementId))
    : agents;

  const upload = useMutation({
    mutationFn: async () => {
      if (!fichier) throw new Error('Pièce principale obligatoire');
      const body: CourrierCreationBody = {
        sens,
        ref_externe: refExterne || null,
        categorie_id: categorieId ? Number(categorieId) : null,
        objet,
        mots_cles: motsCles || null,
        observations: observations || null,
        date_courrier: dateCourrier || null,
        date_arrivee: sens === 'entrant' ? dateArrivee || null : null,
        date_limite: dateLimite || null,
        correspondant_id: sens === 'interne' ? null : Number(correspondantId),
        departement_destinataire_id: departementId ? Number(departementId) : null,
        agent_destinataire_id: Number(agentDestinataireId),
        document_titre: documentTitre,
        document_categorie_id: Number(documentCategorieId),
        a_faire_valider: aFaireValider,
      };
      return creerCourrier(fichier, body, (p) => setProgression(p));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['courriers'] });
      navigate('/courriers');
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    if (!fichier) {
      setErreur('La pièce principale est obligatoire.');
      return;
    }
    if (!objet.trim()) {
      setErreur("L'objet est obligatoire.");
      return;
    }
    if (sens !== 'interne' && !correspondantId) {
      setErreur("Un correspondant est obligatoire pour un courrier entrant ou sortant.");
      return;
    }
    if (!agentDestinataireId) {
      setErreur('Un agent destinataire est obligatoire.');
      return;
    }
    if (!documentTitre.trim() || !documentCategorieId) {
      setErreur('Titre et catégorie du document obligatoires.');
      return;
    }
    upload.mutate();
  }

  function selFichier(f: File | null) {
    setFichier(f);
    if (f && !documentTitre) {
      setDocumentTitre(f.name.replace(/\.[^.]+$/, ''));
    }
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <PageHeader
        titre="Nouveau courrier"
        sousTitre="Enregistre un courrier entrant, sortant ou interne. La pièce principale est obligatoire."
      />

      <form onSubmit={onSubmit} className="space-y-6">
        {/* Sens */}
        <Card>
          <CardHeader>
            <CardTitle>Type de courrier</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {SENS_OPTIONS.map((opt) => {
                const actif = sens === opt.code;
                return (
                  <button
                    key={opt.code}
                    type="button"
                    onClick={() => setSens(opt.code)}
                    className={cn(
                      'rounded-xl border p-3 text-left transition-all',
                      actif
                        ? 'border-brand-300 bg-brand-50 ring-2 ring-brand-100'
                        : 'border-slate-200 bg-white hover:border-slate-300',
                    )}
                  >
                    <p className="text-sm font-semibold text-slate-900 mb-1">{opt.libelle}</p>
                    <p className="text-xs text-slate-500">{opt.description}</p>
                  </button>
                );
              })}
            </div>
          </CardBody>
        </Card>

        {/* Métadonnées principales */}
        <Card>
          <CardHeader>
            <CardTitle>Métadonnées</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            <Input
              label="Objet *"
              value={objet}
              onChange={(e) => setObjet(e.target.value)}
              required
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Référence externe"
                value={refExterne}
                onChange={(e) => setRefExterne(e.target.value)}
                placeholder="Référence portée par le courrier"
              />
              <Select
                label="Catégorie"
                value={categorieId}
                onChange={(e) => setCategorieId(e.target.value)}
              >
                <option value="">— aucune —</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.libelle}
                  </option>
                ))}
              </Select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Input
                label="Date du courrier"
                type="date"
                value={dateCourrier}
                onChange={(e) => setDateCourrier(e.target.value)}
              />
              {sens === 'entrant' && (
                <Input
                  label="Date d'arrivée"
                  type="date"
                  value={dateArrivee}
                  onChange={(e) => setDateArrivee(e.target.value)}
                />
              )}
              <Input
                label="Date limite de traitement"
                type="date"
                value={dateLimite}
                onChange={(e) => setDateLimite(e.target.value)}
              />
            </div>

            <Input
              label="Mots-clés"
              value={motsCles}
              onChange={(e) => setMotsCles(e.target.value)}
            />

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Observations
              </label>
              <textarea
                className="block w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                rows={2}
                value={observations}
                onChange={(e) => setObservations(e.target.value)}
              />
            </div>
          </CardBody>
        </Card>

        {/* Correspondant (entrant/sortant uniquement) */}
        {sens !== 'interne' && (
          <Card>
            <CardHeader>
              <CardTitle>Correspondant</CardTitle>
            </CardHeader>
            <CardBody>
              <div className="flex gap-2 items-end">
                <div className="flex-1">
                  <Select
                    label="Correspondant *"
                    value={correspondantId}
                    onChange={(e) => setCorrespondantId(e.target.value)}
                    required
                  >
                    <option value="">— choisir —</option>
                    {correspondants.map((c) => (
                      <option key={c.id} value={c.id}>
                        {libelleCorrespondant(c)}
                      </option>
                    ))}
                  </Select>
                </div>
                <Button
                  type="button"
                  variante="secondaire"
                  onClick={() => setModalCorrespondant(true)}
                  className="shrink-0"
                >
                  <Plus className="h-4 w-4" /> Nouveau
                </Button>
              </div>
            </CardBody>
          </Card>
        )}

        {/* Destinataire */}
        <Card>
          <CardHeader>
            <CardTitle>Destinataire</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Select
                label="Département"
                value={departementId}
                onChange={(e) => setDepartementId(e.target.value)}
              >
                <option value="">— tous —</option>
                {departements.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.libelle}
                  </option>
                ))}
              </Select>
              <Select
                label="Agent destinataire *"
                value={agentDestinataireId}
                onChange={(e) => setAgentDestinataireId(e.target.value)}
                required
              >
                <option value="">— choisir —</option>
                {agentsFiltres.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.prenom} {a.nom}
                  </option>
                ))}
              </Select>
            </div>
          </CardBody>
        </Card>

        {/* Pièce principale */}
        <Card>
          <CardHeader>
            <CardTitle>
              Pièce principale <Badge variante="erreur" className="ml-2">Obligatoire</Badge>
            </CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            <DropZone fichier={fichier} onChange={selFichier} tailleMaxMo={TAILLE_MAX_MO} />
            <Input
              label="Titre du document *"
              value={documentTitre}
              onChange={(e) => setDocumentTitre(e.target.value)}
              required
            />
            <div className="flex gap-2 items-end">
              <div className="flex-1">
                <Select
                  label="Catégorie du document *"
                  value={documentCategorieId}
                  onChange={(e) => setDocumentCategorieId(e.target.value)}
                  required
                >
                  <option value="">— choisir —</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.libelle}
                    </option>
                  ))}
                </Select>
              </div>
              <Button
                type="button"
                variante="secondaire"
                onClick={() => setModalCategorieDoc(true)}
                className="shrink-0"
              >
                <Plus className="h-4 w-4" /> Nouvelle
              </Button>
            </div>

            {upload.isPending && progression > 0 && (
              <div>
                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-brand-500 transition-all"
                    style={{ width: `${Math.round(progression * 100)}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1 text-right">
                  {Math.round(progression * 100)} %
                </p>
              </div>
            )}
          </CardBody>
        </Card>

        {/* PRD-06B : workflow validation optionnel */}
        <Card>
          <CardBody className="p-4">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={aFaireValider}
                onChange={(e) => setAFaireValider(e.target.checked)}
                className="rounded border-slate-300 text-brand-600 focus:ring-brand-500 mt-0.5"
              />
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-900">
                  À faire valider avant l'envoi
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Le destinataire devra demander la validation à un agent
                  avant de pouvoir envoyer. Utile pour les courriers
                  sortants qui nécessitent un visa hiérarchique.
                </p>
              </div>
            </label>
          </CardBody>
        </Card>

        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}

        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variante="secondaire"
            onClick={() => navigate('/courriers')}
            disabled={upload.isPending}
          >
            Annuler
          </Button>
          <Button type="submit" chargement={upload.isPending} disabled={!fichier}>
            Enregistrer le courrier
          </Button>
        </div>
      </form>

      <ModalNouveauCorrespondant
        ouvert={modalCorrespondant}
        onFermer={() => setModalCorrespondant(false)}
        onCree={(c) => {
          setCorrespondantId(String(c.id));
          setModalCorrespondant(false);
        }}
      />

      <ModalNouvelleCategorieSimple
        ouvert={modalCategorieDoc}
        onFermer={() => setModalCategorieDoc(false)}
        onCree={(id) => {
          setDocumentCategorieId(String(id));
          setModalCategorieDoc(false);
        }}
      />
    </div>
  );
}

function libelleCorrespondant(c: Correspondant): string {
  if (c.raison_sociale) return c.raison_sociale;
  return `${c.prenom ?? ''} ${c.nom ?? ''}`.trim() || '(sans nom)';
}

// ---------------------------------------------------------------------------
// Modal Nouveau correspondant
// ---------------------------------------------------------------------------

function ModalNouveauCorrespondant({
  ouvert,
  onFermer,
  onCree,
}: {
  ouvert: boolean;
  onFermer: () => void;
  onCree: (c: Correspondant) => void;
}) {
  const queryClient = useQueryClient();
  const [typeId, setTypeId] = useState(1);
  const [raisonSociale, setRaisonSociale] = useState('');
  const [nom, setNom] = useState('');
  const [prenom, setPrenom] = useState('');
  const [civilite, setCivilite] = useState('');
  const [email, setEmail] = useState('');
  const [telephone, setTelephone] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => {
      const body: CorrespondantCreation = {
        type_id: typeId,
        raison_sociale: typeId === 1 ? raisonSociale : null,
        civilite: typeId === 2 ? civilite || null : null,
        nom: typeId === 2 ? nom : null,
        prenom: typeId === 2 ? prenom || null : null,
        email: email || null,
        telephone: telephone || null,
      };
      return creerCorrespondant(body);
    },
    onSuccess: (c) => {
      queryClient.invalidateQueries({ queryKey: ['correspondants'] });
      onCree(c);
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  return (
    <Modal ouvert={ouvert} onFermer={onFermer} titre="Nouveau correspondant" largeur="md">
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          setErreur(null);
          mutation.mutate();
        }}
        className="space-y-4"
      >
        <Select label="Type *" value={typeId} onChange={(e) => setTypeId(Number(e.target.value))}>
          <option value={1}>Personne morale</option>
          <option value={2}>Personne physique</option>
        </Select>

        {typeId === 1 ? (
          <Input
            label="Raison sociale *"
            value={raisonSociale}
            onChange={(e) => setRaisonSociale(e.target.value)}
            required
          />
        ) : (
          <div className="grid grid-cols-3 gap-3">
            <Input
              label="Civilité"
              value={civilite}
              onChange={(e) => setCivilite(e.target.value)}
              placeholder="M. Mme…"
            />
            <Input
              label="Prénom"
              value={prenom}
              onChange={(e) => setPrenom(e.target.value)}
            />
            <Input
              label="Nom *"
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              required
            />
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input
            label="Téléphone"
            type="tel"
            value={telephone}
            onChange={(e) => setTelephone(e.target.value)}
          />
        </div>

        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button type="button" variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button type="submit" chargement={mutation.isPending}>
            Créer
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ModalNouvelleCategorieSimple({
  ouvert,
  onFermer,
  onCree,
}: {
  ouvert: boolean;
  onFermer: () => void;
  onCree: (id: number) => void;
}) {
  const queryClient = useQueryClient();
  const [libelle, setLibelle] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => creerCategorie({ libelle, description: null }),
    onSuccess: (c) => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      onCree(c.id);
      setLibelle('');
    },
    onError: (err) => setErreur(extraireMessageErreur(err)),
  });

  return (
    <Modal ouvert={ouvert} onFermer={onFermer} titre="Nouvelle catégorie" largeur="sm">
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          setErreur(null);
          mutation.mutate();
        }}
        className="space-y-4"
      >
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
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button type="button" variante="secondaire" onClick={onFermer}>
            Annuler
          </Button>
          <Button type="submit" chargement={mutation.isPending}>
            Créer
          </Button>
        </div>
      </form>
    </Modal>
  );
}
