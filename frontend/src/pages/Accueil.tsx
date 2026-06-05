import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Clock,
  FileText,
  Mail,
  Sparkles,
  Users,
} from 'lucide-react';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { StatsCard } from '@/components/ui/StatsCard';
import { PageHeader } from '@/components/ui/PageHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { Badge } from '@/components/ui/Badge';
import { listerDocuments } from '@/api/documents';
import { useAuth } from '@/auth/useAuth';
import { formatDateTime } from '@/lib/utils';

function salutation(prenom: string): string {
  const h = new Date().getHours();
  if (h < 6) return `Bonsoir ${prenom}`;
  if (h < 12) return `Bonjour ${prenom}`;
  if (h < 18) return `Bon après-midi ${prenom}`;
  return `Bonsoir ${prenom}`;
}

export default function Accueil() {
  const { agent } = useAuth();
  const { data: documents = [] } = useQuery({
    queryKey: ['documents', { limit: 5 }],
    queryFn: () => listerDocuments({ limit: 5 }),
  });

  if (!agent) return null;

  return (
    <div className="p-6 space-y-8">
      <PageHeader
        titre={salutation(agent.prenom)}
        sousTitre="Voici l'aperçu de ton espace de travail aujourd'hui."
        fil={
          <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700 ring-1 ring-inset ring-brand-200">
            <Sparkles className="h-3 w-3" />
            {new Date().toLocaleDateString('fr-FR', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </span>
        }
      />

      {/* KPI */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          libelle="Courriers à traiter"
          valeur="0"
          icone={Mail}
          ton="brand"
          legende="Aucun courrier en attente"
        />
        <StatsCard
          libelle="Documents indexés"
          valeur={documents.length}
          icone={FileText}
          ton="sky"
          legende="Recherche plein texte active"
        />
        <StatsCard
          libelle="En retard"
          valeur="0"
          icone={Clock}
          ton="amber"
          legende="À traiter en priorité"
        />
        <StatsCard
          libelle="Mon rôle"
          valeur={agent.role === 'superviseur' ? 'Admin' : agent.role === 'archiviste' ? 'Archi.' : 'Agent'}
          icone={Users}
          ton="emerald"
          legende="Permissions actives"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Courriers à traiter */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Courriers à traiter</CardTitle>
            <Link
              to="/courriers"
              className="text-xs font-medium text-brand-600 hover:text-brand-700 inline-flex items-center gap-1"
            >
              Tout voir <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardBody className="p-0">
            <EmptyState
              icone={Mail}
              titre="Aucun courrier à traiter"
              message="Le module Courriers sera disponible avec PRD-06. Tu pourras enregistrer des courriers entrants/sortants/internes et les router aux agents concernés."
            />
          </CardBody>
        </Card>

        {/* Derniers documents */}
        <Card>
          <CardHeader>
            <CardTitle>Derniers documents</CardTitle>
            <Link
              to="/documents"
              className="text-xs font-medium text-brand-600 hover:text-brand-700 inline-flex items-center gap-1"
            >
              Tout voir <ArrowRight className="h-3 w-3" />
            </Link>
          </CardHeader>
          <CardBody className="p-0">
            {documents.length === 0 ? (
              <EmptyState
                icone={FileText}
                titre="Aucun document"
                message="Commence par uploader ton premier document."
              />
            ) : (
              <ul className="divide-y divide-slate-100">
                {documents.slice(0, 5).map((d) => (
                  <li key={d.id}>
                    <Link
                      to="/documents"
                      className="flex items-start gap-3 px-5 py-3 hover:bg-slate-50 transition-colors"
                    >
                      <div className="h-9 w-9 shrink-0 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-slate-900 truncate">
                          {d.titre}
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {formatDateTime(d.created_at)}
                        </p>
                      </div>
                      {d.confidentiel && <Badge variante="attention">Confidentiel</Badge>}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
