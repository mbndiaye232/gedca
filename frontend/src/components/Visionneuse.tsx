import { useEffect, useState } from 'react';
import { Document as PdfDocument, Page as PdfPage, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, Download, ZoomIn, ZoomOut } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { telechargerContenu } from '@/api/documents';
import type { Document } from '@/api/types';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Worker pdf.js — récupéré depuis CDN. En SaaS multi-tenant on bundle plutôt
// le worker dans /public ; pour le dev on prend la version exacte de pdfjs-dist
// inclue avec react-pdf.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface Props {
  ouvert: boolean;
  document: Document | null;
  onFermer: () => void;
}

export function Visionneuse({ ouvert, document: doc, onFermer }: Props) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(0);
  const [echelle, setEchelle] = useState(1.0);

  // Récupère le contenu déchiffré quand on ouvre
  useEffect(() => {
    if (!ouvert || !doc) {
      // Cleanup
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      setBlobUrl(null);
      setErreur(null);
      setPage(1);
      setPages(0);
      setEchelle(1.0);
      return;
    }

    let revoked = false;
    setChargement(true);
    setErreur(null);
    telechargerContenu(doc.id)
      .then((blob) => {
        if (revoked) return;
        const url = URL.createObjectURL(blob);
        setBlobUrl(url);
      })
      .catch((err) => {
        if (revoked) return;
        setErreur(err?.response?.data?.detail ?? 'Impossible de charger le contenu');
      })
      .finally(() => {
        if (!revoked) setChargement(false);
      });

    return () => {
      revoked = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ouvert, doc?.id]);

  function telecharger() {
    if (!blobUrl || !doc) return;
    const a = window.document.createElement('a');
    a.href = blobUrl;
    a.download = doc.titre || `document-${doc.id}`;
    a.click();
  }

  if (!doc) return null;

  const estPdf = doc.mime === 'application/pdf';
  const estImage = doc.mime.startsWith('image/');

  return (
    <Modal ouvert={ouvert} onFermer={onFermer} titre={doc.titre} largeur="lg">
      <div className="space-y-4">
        {/* Barre d'outils */}
        <div className="flex items-center justify-between gap-3 border-b pb-3">
          <div className="text-xs text-gray-500">
            {doc.mime} · {Math.round(doc.taille_octets / 1024)} Ko
          </div>
          <div className="flex items-center gap-2">
            {estPdf && pages > 0 && (
              <>
                <Button
                  variante="fantome"
                  taille="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  title="Page précédente"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm font-mono">
                  {page} / {pages}
                </span>
                <Button
                  variante="fantome"
                  taille="sm"
                  onClick={() => setPage((p) => Math.min(pages, p + 1))}
                  disabled={page >= pages}
                  title="Page suivante"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </>
            )}
            {(estPdf || estImage) && (
              <>
                <Button
                  variante="fantome"
                  taille="sm"
                  onClick={() => setEchelle((s) => Math.max(0.5, s - 0.2))}
                  title="Réduire"
                >
                  <ZoomOut className="h-4 w-4" />
                </Button>
                <Button
                  variante="fantome"
                  taille="sm"
                  onClick={() => setEchelle((s) => Math.min(3, s + 0.2))}
                  title="Agrandir"
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
              </>
            )}
            <Button variante="secondaire" taille="sm" onClick={telecharger}>
              <Download className="h-4 w-4" /> Télécharger
            </Button>
          </div>
        </div>

        {/* Contenu */}
        {chargement && (
          <div className="py-16 text-center text-gray-500">Chargement du contenu…</div>
        )}
        {erreur && (
          <div className="py-8 text-center">
            <p className="text-red-700 text-sm">{erreur}</p>
          </div>
        )}
        {!chargement && !erreur && blobUrl && (
          <div className="flex justify-center bg-gray-100 rounded-lg overflow-auto max-h-[70vh]">
            {estPdf && (
              <PdfDocument
                file={blobUrl}
                onLoadSuccess={({ numPages }) => setPages(numPages)}
                onLoadError={(e) => setErreur(`Erreur PDF : ${e.message}`)}
                loading={
                  <div className="p-8 text-gray-500">Préparation de la visionneuse PDF…</div>
                }
              >
                <PdfPage
                  pageNumber={page}
                  scale={echelle}
                  renderAnnotationLayer
                  renderTextLayer
                />
              </PdfDocument>
            )}
            {estImage && (
              <img
                src={blobUrl}
                alt={doc.titre}
                style={{ transform: `scale(${echelle})`, transformOrigin: 'top center' }}
                className="max-w-full h-auto"
              />
            )}
            {!estPdf && !estImage && (
              <div className="p-8 text-center text-gray-600">
                <p className="mb-2">
                  Ce type de fichier ne peut pas être prévisualisé en ligne.
                </p>
                <Button onClick={telecharger}>
                  <Download className="h-4 w-4" /> Télécharger pour ouvrir
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
