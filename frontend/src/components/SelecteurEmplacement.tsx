import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Folder } from 'lucide-react';
import {
  listerBoites,
  listerDossiers,
  listerLocaux,
  listerRayons,
  listerSites,
  listerSousDossiers,
} from '@/api/archivage';
import type { Boite, Dossier, Local, Rayon, Site, SousDossier } from '@/api/types';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';

interface Props {
  ouvert: boolean;
  onFermer: () => void;
  /** Appelé quand l'utilisateur valide. Reçoit (id, codeDotté, libellé). */
  onSelectionner: (sousDossierId: number, code: string, libelle: string) => void;
}

/**
 * Sélecteur d'emplacement physique en cascade Site → Sous-dossier.
 *
 * Utilisé depuis :
 * - DocumentNouveau (upload)
 * - Document édition
 *
 * Permet de retrouver rapidement un sous-dossier en parcourant la hiérarchie
 * via 5 combos cascade (le 6ème niveau, le sous-dossier, est la sélection finale).
 */
export function SelecteurEmplacement({ ouvert, onFermer, onSelectionner }: Props) {
  const [siteId, setSiteId] = useState<string>('');
  const [localId, setLocalId] = useState<string>('');
  const [rayonId, setRayonId] = useState<string>('');
  const [boiteId, setBoiteId] = useState<string>('');
  const [dossierId, setDossierId] = useState<string>('');
  const [sdId, setSdId] = useState<string>('');

  const { data: sites = [] } = useQuery({
    queryKey: ['archivage', 'sites'],
    queryFn: listerSites,
    enabled: ouvert,
  });
  const { data: locaux = [] } = useQuery({
    queryKey: ['archivage', 'locaux', siteId],
    queryFn: () => listerLocaux(Number(siteId)),
    enabled: ouvert && !!siteId,
  });
  const { data: rayons = [] } = useQuery({
    queryKey: ['archivage', 'rayons', localId],
    queryFn: () => listerRayons(Number(localId)),
    enabled: ouvert && !!localId,
  });
  const { data: boites = [] } = useQuery({
    queryKey: ['archivage', 'boites', rayonId],
    queryFn: () => listerBoites(Number(rayonId)),
    enabled: ouvert && !!rayonId,
  });
  const { data: dossiers = [] } = useQuery({
    queryKey: ['archivage', 'dossiers', boiteId],
    queryFn: () => listerDossiers(Number(boiteId)),
    enabled: ouvert && !!boiteId,
  });
  const { data: sousDossiers = [] } = useQuery({
    queryKey: ['archivage', 'sd', dossierId],
    queryFn: () => listerSousDossiers(Number(dossierId)),
    enabled: ouvert && !!dossierId,
  });

  function valider() {
    const site = sites.find((s) => s.id === Number(siteId));
    const loc = locaux.find((l) => l.id === Number(localId));
    const r = rayons.find((x) => x.id === Number(rayonId));
    const b = boites.find((x) => x.id === Number(boiteId));
    const d = dossiers.find((x) => x.id === Number(dossierId));
    const sd = sousDossiers.find((x) => x.id === Number(sdId));
    if (!site || !loc || !r || !b || !d || !sd) return;

    const code = [
      String(site.numero).padStart(2, '0'),
      String(loc.numero).padStart(2, '0'),
      String(r.numero).padStart(2, '0'),
      String(b.numero).padStart(3, '0'),
      String(d.numero).padStart(2, '0'),
      String(sd.numero).padStart(2, '0'),
    ].join('.');
    onSelectionner(sd.id, code, sd.libelle);
  }

  function reinitialiser(niveau: 'site' | 'local' | 'rayon' | 'boite' | 'dossier') {
    if (niveau === 'site') { setLocalId(''); setRayonId(''); setBoiteId(''); setDossierId(''); setSdId(''); }
    if (niveau === 'local') { setRayonId(''); setBoiteId(''); setDossierId(''); setSdId(''); }
    if (niveau === 'rayon') { setBoiteId(''); setDossierId(''); setSdId(''); }
    if (niveau === 'boite') { setDossierId(''); setSdId(''); }
    if (niveau === 'dossier') { setSdId(''); }
  }

  const peutValider = !!sdId;

  return (
    <Modal ouvert={ouvert} onFermer={onFermer} titre="Choisir un emplacement physique" largeur="lg">
      <div className="space-y-3">
        <p className="text-sm text-gray-600">
          Parcours la hiérarchie pour sélectionner le sous-dossier où le document
          sera physiquement rangé.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Select
            label="1. Site"
            value={siteId}
            onChange={(e) => { setSiteId(e.target.value); reinitialiser('site'); }}
          >
            <option value="">— choisir —</option>
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {String(s.numero).padStart(2, '0')} · {s.libelle}
              </option>
            ))}
          </Select>

          <Select
            label="2. Local"
            value={localId}
            onChange={(e) => { setLocalId(e.target.value); reinitialiser('local'); }}
            disabled={!siteId}
          >
            <option value="">— choisir —</option>
            {locaux.map((l) => (
              <option key={l.id} value={l.id}>
                {String(l.numero).padStart(2, '0')} · {l.libelle}
              </option>
            ))}
          </Select>

          <Select
            label="3. Rayon"
            value={rayonId}
            onChange={(e) => { setRayonId(e.target.value); reinitialiser('rayon'); }}
            disabled={!localId}
          >
            <option value="">— choisir —</option>
            {rayons.map((r) => (
              <option key={r.id} value={r.id}>
                {String(r.numero).padStart(2, '0')} · {r.libelle}
              </option>
            ))}
          </Select>

          <Select
            label="4. Boîte"
            value={boiteId}
            onChange={(e) => { setBoiteId(e.target.value); reinitialiser('boite'); }}
            disabled={!rayonId}
          >
            <option value="">— choisir —</option>
            {boites.map((b) => (
              <option key={b.id} value={b.id}>
                {String(b.numero).padStart(3, '0')} · {b.libelle}
              </option>
            ))}
          </Select>

          <Select
            label="5. Dossier"
            value={dossierId}
            onChange={(e) => { setDossierId(e.target.value); reinitialiser('dossier'); }}
            disabled={!boiteId}
          >
            <option value="">— choisir —</option>
            {dossiers.map((d) => (
              <option key={d.id} value={d.id}>
                {String(d.numero).padStart(2, '0')} · {d.libelle}
              </option>
            ))}
          </Select>

          <Select
            label="6. Sous-dossier"
            value={sdId}
            onChange={(e) => setSdId(e.target.value)}
            disabled={!dossierId}
          >
            <option value="">— choisir —</option>
            {sousDossiers.map((sd) => (
              <option key={sd.id} value={sd.id}>
                {String(sd.numero).padStart(2, '0')} · {sd.libelle}
              </option>
            ))}
          </Select>
        </div>

        {sousDossiers.length === 0 && dossierId && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
            <Folder className="inline h-4 w-4 mr-1" />
            Aucun sous-dossier dans ce dossier. Crée-en un depuis l'écran Archivage.
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t">
          <Button type="button" variante="secondaire" onClick={onFermer}>Annuler</Button>
          <Button type="button" onClick={valider} disabled={!peutValider}>
            Sélectionner
          </Button>
        </div>
      </div>
    </Modal>
  );
}
