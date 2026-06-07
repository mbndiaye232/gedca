import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Eye, FileText, FolderUp, MapPin, Plus, Search, Trash2 } from 'lucide-react';
import { listerDocuments, supprimerDocument } from '@/api/documents';
import { listerCategories } from '@/api/referentiels';
import type { Document } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Card, CardBody } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { Visionneuse } from '@/components/Visionneuse';
import { DetailEmplacement } from '@/components/DetailEmplacement';
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
  const [emplacementDoc, setEmplacementDoc] = useState<Document | null>(null);

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

  const peutUploader = agent?.role === 'archiviste' || agent?.role === 'superviseur';
  const peutSupprimer = agent?.role === 'superviseur';

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        titre="Documents"
        sousTitre="Bibliothèque chiffrée. Recherche plein texte sur titre, mots-clés et contenu OCR."
        actions={
          peutUploader && (
            <div className="flex gap-2">
              <Link to="/documents/importer">
                <Button variante="secondaire">
                  <FolderUp className="h-4 w-4" /> Importer un dossier
                </Button>
              </Link>
              <Link to="/documents/nouveau">
                <Button>
                  <Plus className="h-4 w-4" /> Nouveau document
                </Button>
              </Link>
            </div>
          )
        }
      />

      {/* Filtres */}
      <Card>
        <CardBody className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
            <div className="flex-1">
              <Input
                label="Rechercher"
                placeholder="Mot-clé, contenu, titre…"
                value={recherche}
                onChange={(e) => setRecherche(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') setRechercheActive(recherche.trim());
                }}
                icone={<Search className="h-4 w-4" />}
              />
            </div>
            <div className="sm:w-64">
              <Select
                label="Catégorie"
                value={categorieFiltre}
                onChange={(e) => setCategorieFiltre(e.target.value)}
              >
                <option value="">Toutes les catégories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.libelle}</option>
                ))}
              </Select>
            </div>
            <Button onClick={() => setRechercheActive(recherche.trim())} variante="secondaire">
              Rechercher
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Liste */}
      <Card className="overflow-hidden">
        {isLoading && (
          <div className="p-8 text-center text-slate-500 text-sm">Chargement…</div>
        )}
        {!isLoading && documents.length === 0 && (
          <EmptyState
            icone={FileText}
            titre={
              rechercheActive
                ? `Aucun document pour « ${rechercheActive} »`
                : 'Aucun document'
            }
            message={
              peutUploader
                ? 'Commence par uploader ton premier document avec « Nouveau document ».'
                : 'Aucun document dans la bibliothèque pour l\'instant.'
            }
            action={
              peutUploader && (
                <Link to="/documents/nouveau">
                  <Button>
                    <Plus className="h-4 w-4" /> Nouveau document
                  </Button>
                </Link>
              )
            }
          />
        )}
        {!isLoading && documents.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50">
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Titre
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Type
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Taille
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Date doc
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Emplacement
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Statut
                  </th>
                  <th className="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Ajouté
                  </th>
                  <th className="px-5 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-start gap-3">
                        <div className="h-8 w-8 shrink-0 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center">
                          <FileText className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-slate-900 font-medium truncate">{d.titre}</span>
                            {d.confidentiel && (
                              <Badge variante="attention" pastille>
                                Confidentiel
                              </Badge>
                            )}
                          </div>
                          {d.mots_cles && (
                            <p className="text-xs text-slate-500 mt-0.5 truncate max-w-md">
                              {d.mots_cles}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-slate-600 font-mono text-xs">{d.mime}</td>
                    <td className="px-5 py-3.5 text-slate-600 text-xs">
                      {formatTaille(d.taille_octets)}
                    </td>
                    <td className="px-5 py-3.5 text-slate-600">{formatDate(d.date_document)}</td>
                    <td className="px-5 py-3.5">
                      {d.emplacement ? (
                        <button
                          type="button"
                          onClick={() => setEmplacementDoc(d)}
                          className="flex items-start gap-1.5 max-w-xs text-left rounded-lg px-1.5 py-1 -mx-1.5 -my-1 hover:bg-brand-50 transition-colors group"
                          title={`Détail : ${d.emplacement.site.libelle} → ${d.emplacement.sous_dossier.libelle}`}
                        >
                          <MapPin className="h-3.5 w-3.5 text-brand-600 mt-0.5 shrink-0 group-hover:scale-110 transition-transform" />
                          <div className="min-w-0">
                            <p className="font-mono text-xs text-slate-700 group-hover:text-brand-700">
                              {d.emplacement.code_complet}
                            </p>
                            <p className="text-xs text-slate-500 truncate">
                              {d.emplacement.sous_dossier.libelle}
                            </p>
                          </div>
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <StatutBadge statut={d.statut} />
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 text-xs">
                      {formatDateTime(d.created_at)}
                    </td>
                    <td className="px-5 py-3.5 text-right">
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
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Visionneuse
        ouvert={visionneuseDoc !== null}
        document={visionneuseDoc}
        onFermer={() => setVisionneuseDoc(null)}
      />

      <DetailEmplacement
        ouvert={emplacementDoc !== null}
        emplacement={emplacementDoc?.emplacement ?? null}
        onFermer={() => setEmplacementDoc(null)}
      />
    </div>
  );
}

function StatutBadge({ statut }: { statut: string }) {
  if (statut === 'pret') return <Badge variante="succes" pastille>Prêt</Badge>;
  if (statut === 'en_cours') return <Badge variante="info" pastille>En traitement</Badge>;
  if (statut === 'quarantaine') return <Badge variante="erreur" pastille>Quarantaine</Badge>;
  return <Badge>{statut}</Badge>;
}
