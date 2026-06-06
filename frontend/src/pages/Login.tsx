import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Lock, ShieldCheck, User } from 'lucide-react';
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
    <div className="min-h-screen flex bg-slate-50">
      {/* Volet de gauche — formulaire */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-8 animate-fade-in">
          <div>
            <div className="inline-flex items-center gap-2.5 mb-6">
              <div className="h-10 w-10 rounded-xl bg-gradient-brand shadow-sm flex items-center justify-center text-white font-bold tracking-tight">
                G
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-900 tracking-tight leading-none">
                  GEDCA
                </h1>
                <p className="text-[10px] uppercase tracking-wider text-slate-400 mt-1">
                  Gestion documentaire
                </p>
              </div>
            </div>

            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Bienvenue</h2>
            <p className="text-sm text-slate-500 mt-1">
              Connecte-toi pour accéder à ton espace de travail.
            </p>
          </div>

          <form onSubmit={onSubmit} className="space-y-5">
            <Input
              label="Login"
              type="text"
              autoComplete="username"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              required
              autoFocus
              icone={<User className="h-4 w-4" />}
              placeholder="admin"
            />
            <Input
              label="Mot de passe"
              type="password"
              autoComplete="current-password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              required
              icone={<Lock className="h-4 w-4" />}
              placeholder="••••••••"
            />

            {erreur && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2.5 text-sm text-red-700 animate-fade-in">
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

          <p className="text-xs text-slate-400 text-center">
            Problème de connexion ? Contacte ton administrateur.
          </p>
        </div>
      </div>

      {/* Volet de droite — illustration / argumentaire (caché sur mobile) */}
      <div className="hidden lg:flex flex-1 relative overflow-hidden bg-gradient-brand">
        <div className="absolute inset-0 bg-gradient-mesh opacity-30" aria-hidden />
        <div className="relative z-10 flex flex-col justify-between p-12 text-white">
          <div className="space-y-1">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium backdrop-blur-sm">
              <ShieldCheck className="h-3.5 w-3.5" />
              Chiffrement AES-256-GCM
            </span>
          </div>

          <div className="space-y-6 max-w-md">
            <h2 className="text-4xl font-bold tracking-tight leading-tight">
              Gérez vos documents, courriers et archives en un seul endroit.
            </h2>
            <p className="text-white/80 text-lg">
              Une plateforme unifiée pour la GED, la GEC et l'archivage physique,
              avec recherche plein texte et sémantique.
            </p>

            <div className="grid grid-cols-3 gap-4 pt-4">
              {[
                { v: 'GED', l: 'Documents chiffrés' },
                { v: 'GEC', l: 'Courriers & workflows' },
                { v: '6 niv.', l: 'Archivage physique' },
              ].map((s) => (
                <div
                  key={s.v}
                  className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/15 p-3"
                >
                  <p className="text-2xl font-bold tracking-tight">{s.v}</p>
                  <p className="text-xs text-white/70 mt-0.5">{s.l}</p>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-white/60">
            © {new Date().getFullYear()} GEDCA — Tous droits réservés
          </p>
        </div>
      </div>
    </div>
  );
}
