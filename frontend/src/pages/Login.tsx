import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/auth/useAuth';
import { extraireMessageErreur } from '@/api/client';

export default function Login() {
  const { connecter, estConnecte, enChargement } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [login, setLogin] = useState('');
  const [motDePasse, setMotDePasse] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);

  // Déjà connecté → redirige vers la destination demandée ou /accueil
  if (estConnecte) {
    const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
    return <Navigate to={destination ?? '/accueil'} replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    try {
      await connecter(login, motDePasse);
      const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      navigate(destination ?? '/accueil', { replace: true });
    } catch (err) {
      setErreur(extraireMessageErreur(err, 'Identifiants invalides'));
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8 space-y-6"
      >
        <div className="text-center">
          <h1 className="text-3xl font-bold text-brand-700">GEDCA</h1>
          <p className="text-sm text-gray-500 mt-1">
            Gestion électronique de documents
          </p>
        </div>

        <div className="space-y-4">
          <Input
            label="Login"
            type="text"
            autoComplete="username"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            required
            autoFocus
          />
          <Input
            label="Mot de passe"
            type="password"
            autoComplete="current-password"
            value={motDePasse}
            onChange={(e) => setMotDePasse(e.target.value)}
            required
          />
        </div>

        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {erreur}
          </div>
        )}

        <Button
          type="submit"
          taille="lg"
          chargement={enChargement}
          className="w-full"
        >
          Se connecter
        </Button>
      </form>
    </div>
  );
}
