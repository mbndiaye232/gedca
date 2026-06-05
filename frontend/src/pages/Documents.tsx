import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Eye, Plus, Search, Trash2 } from 'lucide-react';
import { listerDocuments, supprimerDocument } from '@/api/documents';
import { listerCategories } from '@/api/referentiels';
import type { Document } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Visionneuse } from '@/components/Visionneuse';
import { extraireMessageErreur } from '@/api/client';
import { useAuth } from '@/auth/useAuth';
import { formatDate, formatDateTime } from '@/lib/utils';

const TAILLES = ['o', 'Ko', 'Mo', 'Go'] as const;

function formatTaille(octets: number): string {
  let n = octets;
  let i = 0;
  while (n >= 1024 && i < TAILLES.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)} ${TAILLES[i]}`;
}

export default function Documents() {
  const { agent } = useAuth();
  const queryClient = useQueryClient();

  const [recherche, setRecherche] = useState('');
  const [rechercheActive, setRechercheActive] = useState('');
  const [categorieFiltre, setCategorieFiltre] = useState<string>('');
  const [visionneuseDoc, setVisionneuseDoc] = useState<Document | null>(null);

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents', { q: rechercheActive, categorie_id: categorieFiltre || undefined }],
    queryFn: () =>
      listerDocuments({
        q: rechercheActive || undefined,
        categorie_id: categorieFiltre ? Number(categorieFiltre) : undefined,
      }),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: listerCategories,
  });

  const suppression = useMutation({
    mutationFn: supprimerDocument,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['documents'] }),
    onError: (err) => alert(extraireMessageErreur(err)),
  });

  const peutUploader =
    agent?.role === 'archiviste' || agent?.role === 'superviseur';
  const peutSupprimer = agent?.role === 'superviseur';

  function lancerRecherche() {
    setRechercheActive(recherche.trim());
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-gray-600 text-sm mt-1">
            Bibliothèque documentaire chiffrée. Recherche plein texte sur titre, mots-clés et contenu OCR.
          </p>
        </div>
        {peutUploader && (
          <Link to="/documents/nouveau">
            <Button>
              <Plus className="h-4 w-4" /> Nouveau document
            </Button>
          </Link>
        )}
      </div>

      {/* Filtres */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
          <div className="flex-1">
            <Input
              label="Rechercher"
              placeholder="Mot-clé, contenu, titre…"
              value={recherche}
              onChange={(e) => setRecherche(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') lancerRecherche();
              }}
            />
          </div>
          <div className="sm:w-64">
            <Select
              label="Catégorie"
              value={categorieFiltre}
              onChange={(e) => setCategorieFiltre(e.target.value)}
            >
              <option value="">— toutes —</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.libelle}</option>
              ))}
            </Select>
          </div>
          <Button onClick={lancerRecherche} variante="secondaire">
            <Search className="h-4 w-4" /> Rechercher
          </Button>
        </div>
      </Card>

      {/* Liste */}
      <Card>
        {isLoading && (
          <div className="p-8 text-center text-gray-500">Chargement…</div>
        )}
        {!isLoading && documents.length === 0 && (
          <div className="p-8 text-center text-gray-500">
            Aucun document {rechercheActive ? `trouvé pour « ${rechercheActive} »` : 'pour l\'instant'}.
            {peutUploader && (
              <p className="text-sm text-gray-400 mt-2">
                Utilise <strong>Nouveau document</strong> pour en ajouter un.
              </p>
            )}
          </div>
        )}
        {!isLoading && documents.length > 0 && (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3">Titre</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Taille</th>
                <th className="px-4 py-3">Date doc</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3">Ajouté</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {documents.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-900 font-medium">{d.titre}</span>
                      {d.confidentiel && <Badge variante="attention">Confidentiel</Badge>}
                    </div>
                    {d.mots_cles && (
                      <p className="text-xs text-gray-500 mt-0.5 truncate max-w-md">
                        {d.mots_cles}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600 font-mono text-xs">{d.mime}</td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{formatTaille(d.taille_octets)}</td>
                  <td className="px-4 py-3 text-gray-600">{formatDate(d.date_document)}</td>
                  <td className="px-4 py-3">
                    <StatutBadge statut={d.statut} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {formatDateTime(d.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex gap-1">
                      <Button
                        variante="fantome"
                        taille="sm"
                        onClick={() => setVisionneuseDoc(d)}
                        title="Visualiser"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      {peutSupprimer && (
                        <Button
                          variante="fantome"
                          taille="sm"
                          onClick={() => {
                            if (confirm(`Supprimer le document « ${d.titre} » ?`)) {
                              suppression.mutate(d.id);
                            }
                          }}
                          title="Supprimer"
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
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

      <Visionneuse
        ouvert={visionneuseDoc !== null}
        document={visionneuseDoc}
        onFermer={() => setVisionneuseDoc(null)}
      />
    </div>
  );
}

function StatutBadge({ statut }: { statut: string }) {
  if (statut === 'pret') return <Badge variante="succes">Prêt</Badge>;
  if (statut === 'en_cours') return <Badge variante="info">En traitement</Badge>;
  if (statut === 'quarantaine') return <Badge variante="erreur">Quarantaine</Badge>;
  return <Badge>{statut}</Badge>;
}
