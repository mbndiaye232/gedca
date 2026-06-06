import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronRight, Pencil, Plus, Trash2 } from 'lucide-react';
import {
  creerBoite, creerDossier, creerLocal, creerRayon, creerSite, creerSousDossier,
  listerBoites, listerDossiers, listerLocaux, listerRayons, listerSites, listerSousDossiers,
  majBoite, majDossier, majLocal, majRayon, majSite, majSousDossier,
  supprimerBoite, supprimerDossier, supprimerLocal, supprimerRayon, supprimerSite, supprimerSousDossier,
} from '@/api/archivage';
import { extraireMessageErreur } from '@/api/client';
import type { Boite, Dossier, Local, Rayon, Site, SousDossier } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { useAuth } from '@/auth/useAuth';
import { cn } from '@/lib/utils';

type NiveauKey = 'site' | 'local' | 'rayon' | 'boite' | 'dossier' | 'sd';

interface Selection {
  site?: Site;
  local?: Local;
  rayon?: Rayon;
  boite?: Boite;
  dossier?: Dossier;
  sd?: SousDossier;
}

export default function Archivage() {
  const [sel, setSel] = useState<Selection>({});

  function selectionner(niveau: NiveauKey, item: Site | Local | Rayon | Boite | Dossier | SousDossier) {
    // Reset des niveaux inférieurs quand on change de sélection
    if (niveau === 'site') setSel({ site: item as Site });
    else if (niveau === 'local') setSel({ ...sel, local: item as Local, rayon: undefined, boite: undefined, dossier: undefined, sd: undefined });
    else if (niveau === 'rayon') setSel({ ...sel, rayon: item as Rayon, boite: undefined, dossier: undefined, sd: undefined });
    else if (niveau === 'boite') setSel({ ...sel, boite: item as Boite, dossier: undefined, sd: undefined });
    else if (niveau === 'dossier') setSel({ ...sel, dossier: item as Dossier, sd: undefined });
    else if (niveau === 'sd') setSel({ ...sel, sd: item as SousDossier });
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Archivage physique</h1>
        <p className="text-gray-600 text-sm mt-1">
          Hiérarchie d'emplacements à 6 niveaux. Les numéros sont auto-attribués
          dans l'ordre de création. Format du code complet :{' '}
          <span className="font-mono">SS.LL.RR.BBB.DD.SD</span>.
        </p>
      </div>

      <Fil selection={sel} />

      {/* 6 panneaux côte à côte sur desktop, en colonnes sur mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <PanneauSites selection={sel} onSelect={(s) => selectionner('site', s)} />
        <PanneauLocaux selection={sel} onSelect={(l) => selectionner('local', l)} />
        <PanneauRayons selection={sel} onSelect={(r) => selectionner('rayon', r)} />
        <PanneauBoites selection={sel} onSelect={(b) => selectionner('boite', b)} />
        <PanneauDossiers selection={sel} onSelect={(d) => selectionner('dossier', d)} />
        <PanneauSousDossiers selection={sel} onSelect={(sd) => selectionner('sd', sd)} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Fil d'Ariane
// ---------------------------------------------------------------------------

function Fil({ selection }: { selection: Selection }) {
  const niveaux: { libelle: string; numero: number }[] = [];
  if (selection.site) niveaux.push({ libelle: selection.site.libelle, numero: selection.site.numero });
  if (selection.local) niveaux.push({ libelle: selection.local.libelle, numero: selection.local.numero });
  if (selection.rayon) niveaux.push({ libelle: selection.rayon.libelle, numero: selection.rayon.numero });
  if (selection.boite) niveaux.push({ libelle: selection.boite.libelle, numero: selection.boite.numero });
  if (selection.dossier) niveaux.push({ libelle: selection.dossier.libelle, numero: selection.dossier.numero });
  if (selection.sd) niveaux.push({ libelle: selection.sd.libelle, numero: selection.sd.numero });

  if (niveaux.length === 0) {
    return (
      <Card className="px-4 py-2 text-sm text-gray-500">
        Aucun emplacement sélectionné — commence par choisir un site.
      </Card>
    );
  }

  return (
    <Card className="px-4 py-2 flex items-center gap-2 text-sm flex-wrap">
      {niveaux.map((n, i) => (
        <span key={i} className="inline-flex items-center gap-2">
          <span className="font-mono text-xs text-gray-500">
            {String(n.numero).padStart(i === 3 ? 3 : 2, '0')}
          </span>
          <span className="text-gray-900">{n.libelle}</span>
          {i < niveaux.length - 1 && <ChevronRight className="h-3 w-3 text-gray-400" />}
        </span>
      ))}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Panneaux génériques
// ---------------------------------------------------------------------------

interface PanneauProps<T extends { id: number; numero: number; libelle: string }> {
  titre: string;
  invitation: string;
  disabled?: boolean;
  query: () => Promise<T[]>;
  queryKey: unknown[];
  selectionId?: number;
  onSelect: (item: T) => void;
  onCreer?: (libelle: string) => Promise<T>;
  onMaj?: (id: number, libelle: string) => Promise<T>;
  onSupprimer?: (id: number) => Promise<T>;
  tailleNumero?: number; // 2 ou 3
  peutSupprimer?: boolean;
}

function Panneau<T extends { id: number; numero: number; libelle: string }>({
  titre, invitation, disabled, query, queryKey, selectionId, onSelect,
  onCreer, onMaj, onSupprimer, tailleNumero = 2, peutSupprimer = true,
}: PanneauProps<T>) {
  const queryClient = useQueryClient();
  const [creationOuverte, setCreationOuverte] = useState(false);
  const [edition, setEdition] = useState<T | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const { data: items = [], isLoading, isFetching } = useQuery({
    queryKey,
    queryFn: query,
    enabled: !disabled,
  });

  const supp = useMutation({
    mutationFn: async (id: number) => onSupprimer!(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
    onError: (err) => alert(extraireMessageErreur(err)),
  });

  if (disabled) {
    return (
      <Card className="p-4 opacity-60">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">{titre}</h3>
        </div>
        <p className="text-sm text-gray-400">{invitation}</p>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">{titre}</h3>
        {onCreer && (
          <Button taille="sm" onClick={() => { setErreur(null); setCreationOuverte(true); }}>
            <Plus className="h-4 w-4" /> Ajouter
          </Button>
        )}
      </div>

      {(isLoading || isFetching) && <p className="text-sm text-gray-400">Chargement…</p>}
      {!isLoading && items.length === 0 && (
        <p className="text-sm text-gray-500">Aucun élément. Clique sur « Ajouter ».</p>
      )}

      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item.id}>
            <div
              className={cn(
                'flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer text-sm',
                selectionId === item.id
                  ? 'bg-brand-50 border border-brand-200'
                  : 'hover:bg-gray-50 border border-transparent',
              )}
              onClick={() => onSelect(item)}
            >
              <span className="font-mono text-xs text-gray-500 shrink-0">
                {String(item.numero).padStart(tailleNumero, '0')}
              </span>
              <span className="flex-1 truncate text-gray-900">{item.libelle}</span>
              {onMaj && (
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setEdition(item); setErreur(null); }}
                  className="p-1 rounded hover:bg-gray-200 text-gray-500"
                  title="Renommer"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              )}
              {onSupprimer && peutSupprimer && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`Supprimer « ${item.libelle} » ?`)) supp.mutate(item.id);
                  }}
                  className="p-1 rounded hover:bg-gray-200 text-red-600"
                  title="Supprimer"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      {creationOuverte && onCreer && (
        <FormulaireSaisie
          titre={`Nouveau — ${titre.toLowerCase()}`}
          erreur={erreur}
          onValider={async (libelle) => {
            try {
              await onCreer(libelle);
              queryClient.invalidateQueries({ queryKey });
              setCreationOuverte(false);
            } catch (e) { setErreur(extraireMessageErreur(e)); }
          }}
          onFermer={() => setCreationOuverte(false)}
        />
      )}

      {edition && onMaj && (
        <FormulaireSaisie
          titre={`Renommer — ${edition.libelle}`}
          valeurInitiale={edition.libelle}
          erreur={erreur}
          onValider={async (libelle) => {
            try {
              await onMaj(edition.id, libelle);
              queryClient.invalidateQueries({ queryKey });
              setEdition(null);
            } catch (e) { setErreur(extraireMessageErreur(e)); }
          }}
          onFermer={() => setEdition(null)}
        />
      )}
    </Card>
  );
}

function FormulaireSaisie({
  titre, valeurInitiale = '', erreur, onValider, onFermer,
}: {
  titre: string;
  valeurInitiale?: string;
  erreur: string | null;
  onValider: (libelle: string) => void;
  onFermer: () => void;
}) {
  const [libelle, setLibelle] = useState(valeurInitiale);
  function onSubmit(e: FormEvent) { e.preventDefault(); if (libelle.trim()) onValider(libelle.trim()); }
  return (
    <Modal ouvert titre={titre} onFermer={onFermer} largeur="sm">
      <form onSubmit={onSubmit} className="space-y-3">
        <Input label="Libellé" value={libelle} onChange={(e) => setLibelle(e.target.value)} autoFocus required />
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variante="secondaire" onClick={onFermer}>Annuler</Button>
          <Button type="submit">Valider</Button>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Panneaux concrets — chacun appelle Panneau<T> avec le bon binding API
// ---------------------------------------------------------------------------

function PanneauSites({ selection, onSelect }: { selection: Selection; onSelect: (s: Site) => void }) {
  const { agent } = useAuth();
  const peutSupprimer = agent?.role === 'superviseur';
  return (
    <Panneau<Site>
      titre="1. Sites" invitation="Niveau racine"
      query={listerSites} queryKey={['archivage', 'sites']}
      selectionId={selection.site?.id} onSelect={onSelect}
      onCreer={(libelle) => creerSite(libelle)}
      onMaj={(id, libelle) => majSite(id, { libelle })}
      onSupprimer={supprimerSite}
      peutSupprimer={peutSupprimer}
    />
  );
}

function PanneauLocaux({ selection, onSelect }: { selection: Selection; onSelect: (l: Local) => void }) {
  const { agent } = useAuth();
  const peutSupprimer = agent?.role === 'superviseur';
  return (
    <Panneau<Local>
      titre="2. Locaux / salles" invitation="Sélectionne un site"
      disabled={!selection.site}
      query={() => listerLocaux(selection.site!.id)}
      queryKey={['archivage', 'locaux', selection.site?.id]}
      selectionId={selection.local?.id} onSelect={onSelect}
      onCreer={(libelle) => creerLocal(selection.site!.id, libelle)}
      onMaj={(id, libelle) => majLocal(id, { libelle })}
      onSupprimer={supprimerLocal}
      peutSupprimer={peutSupprimer}
    />
  );
}

function PanneauRayons({ selection, onSelect }: { selection: Selection; onSelect: (r: Rayon) => void }) {
  const { agent } = useAuth();
  const peutSupprimer = agent?.role === 'superviseur';
  return (
    <Panneau<Rayon>
      titre="3. Rayons" invitation="Sélectionne un local"
      disabled={!selection.local}
      query={() => listerRayons(selection.local!.id)}
      queryKey={['archivage', 'rayons', selection.local?.id]}
      selectionId={selection.rayon?.id} onSelect={onSelect}
      onCreer={(libelle) => creerRayon(selection.local!.id, libelle)}
      onMaj={(id, libelle) => majRayon(id, libelle)}
      onSupprimer={supprimerRayon}
      peutSupprimer={peutSupprimer}
    />
  );
}

function PanneauBoites({ selection, onSelect }: { selection: Selection; onSelect: (b: Boite) => void }) {
  const { agent } = useAuth();
  const peutSupprimer = agent?.role === 'superviseur';
  return (
    <Panneau<Boite>
      titre="4. Boîtes (jusqu'à 999)" invitation="Sélectionne un rayon"
      disabled={!selection.rayon}
      query={() => listerBoites(selection.rayon!.id)}
      queryKey={['archivage', 'boites', selection.rayon?.id]}
      selectionId={selection.boite?.id} onSelect={onSelect}
      onCreer={(libelle) => creerBoite(selection.rayon!.id, libelle)}
      onMaj={(id, libelle) => majBoite(id, libelle)}
      onSupprimer={supprimerBoite}
      tailleNumero={3}
      peutSupprimer={peutSupprimer}
    />
  );
}

function PanneauDossiers({ selection, onSelect }: { selection: Selection; onSelect: (d: Dossier) => void }) {
  const { agent } = useAuth();
  const peutSupprimer = agent?.role === 'superviseur';
  return (
    <Panneau<Dossier>
      titre="5. Dossiers" invitation="Sélectionne une boîte"
      disabled={!selection.boite}
      query={() => listerDossiers(selection.boite!.id)}
      queryKey={['archivage', 'dossiers', selection.boite?.id]}
      selectionId={selection.dossier?.id} onSelect={onSelect}
      onCreer={(libelle) => creerDossier(selection.boite!.id, libelle)}
      onMaj={(id, libelle) => majDossier(id, libelle)}
      onSupprimer={supprimerDossier}
      peutSupprimer={peutSupprimer}
    />
  );
}

function PanneauSousDossiers({ selection, onSelect }: { selection: Selection; onSelect: (sd: SousDossier) => void }) {
  const { agent } = useAuth();
  const peutSupprimer = agent?.role === 'superviseur';
  return (
    <Panneau<SousDossier>
      titre="6. Sous-dossiers" invitation="Sélectionne un dossier"
      disabled={!selection.dossier}
      query={() => listerSousDossiers(selection.dossier!.id)}
      queryKey={['archivage', 'sd', selection.dossier?.id]}
      selectionId={selection.sd?.id} onSelect={onSelect}
      onCreer={(libelle) => creerSousDossier(selection.dossier!.id, libelle)}
      onMaj={(id, libelle) => majSousDossier(id, libelle)}
      onSupprimer={supprimerSousDossier}
      peutSupprimer={peutSupprimer}
    />
  );
}
