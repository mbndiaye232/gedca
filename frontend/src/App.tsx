import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api';

interface HealthResponse {
  statut: string;
  version: string;
  mode: string;
}

async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await axios.get<HealthResponse>(`${API_URL}/health`);
  return data;
}

export default function App() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
  });

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-md w-full bg-white rounded-2xl shadow p-8">
        <h1 className="text-3xl font-bold text-brand-700 mb-2">GEDCA</h1>
        <p className="text-sm text-gray-500 mb-6">
          Gestion électronique de documents, courriers et archivage physique.
        </p>

        <div className="border-t pt-4">
          <p className="text-sm font-medium text-gray-700 mb-2">État de l'API</p>
          {isLoading && <p className="text-gray-500">Connexion à l'API…</p>}
          {error && (
            <p className="text-red-600 text-sm">
              Impossible de joindre l'API ({API_URL}). Vérifie que le backend est démarré.
            </p>
          )}
          {data && (
            <div className="text-sm space-y-1">
              <p>
                <span className="text-gray-500">Statut :</span>{' '}
                <span className="font-mono">{data.statut}</span>
              </p>
              <p>
                <span className="text-gray-500">Version :</span>{' '}
                <span className="font-mono">{data.version}</span>
              </p>
              <p>
                <span className="text-gray-500">Mode :</span>{' '}
                <span className="font-mono">{data.mode}</span>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
