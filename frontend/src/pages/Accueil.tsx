import { Mail } from 'lucide-react';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { useAuth } from '@/auth/useAuth';

export default function Accueil() {
  const { agent } = useAuth();
  if (!agent) return null;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Bonjour {agent.prenom}
        </h1>
        <p className="text-gray-600 mt-1">
          Voici les courriers que tu as à traiter.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Courriers à traiter</CardTitle>
        </CardHeader>
        <CardBody>
          {/* TODO PRD-06 : remplacer par la vraie liste avec coloration
              dérivée de @/lib/echeance (classesEcheance) */}
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Mail className="h-12 w-12 text-gray-300 mb-3" />
            <p className="text-gray-500">
              Néant — aucun courrier à traiter pour l'instant.
            </p>
            <p className="text-sm text-gray-400 mt-2">
              Le module Courriers sera disponible avec PRD-06.
            </p>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
