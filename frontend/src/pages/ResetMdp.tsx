import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertCircle, CheckCircle2, Lock } from 'lucide-react';
import { api, extraireMessageErreur } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardBody } from '@/components/ui/Card';

/**
 * Page publique de réinitialisation de mot de passe.
 *
 * URL : `/reset-mdp?token=<token>`
 *
 * Workflow :
 * 1. Au chargement, vérifie le token côté backend (GET /auth/reset-mdp/verifier).
 * 2. Si valide : affiche le formulaire avec le prénom de l'agent.
 * 3. Si invalide : message d'erreur + lien vers /login.
 * 4. À la soumission : POST /auth/reset-mdp/changer → redirection /login.
 */
export default function ResetMdp() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';

  // États du flux
  const [verification, setVerification] = useState<'en_cours' | 'valide' | 'invalide'>(
    'en_cours',
  );
  const [prenom, setPrenom] = useState<string | null>(null);

  // États du formulaire
  const [mdp, setMdp] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState(false);
  const [enCours, setEnCours] = useState(false);

  // Vérification du token au chargement
  useEffect(() => {
    if (!token) {
      setVerification('invalide');
      return;
    }
    api
      .get<{ valide: boolean; prenom: string | null }>(
        '/auth/reset-mdp/verifier',
        { params: { token } },
      )
      .then((res) => {
        if (res.data.valide) {
          setVerification('valide');
          setPrenom(res.data.prenom);
        } else {
          setVerification('invalide');
        }
      })
      .catch(() => setVerification('invalide'));
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    if (mdp.length < 8) {
      setErreur('Le mot de passe doit faire au moins 8 caractères.');
      return;
    }
    if (mdp !== confirmation) {
      setErreur('Les deux mots de passe ne correspondent pas.');
      return;
    }
    setEnCours(true);
    try {
      await api.post('/auth/reset-mdp/changer', {
        token,
        nouveau_mot_de_passe: mdp,
      });
      setSucces(true);
      // Redirection automatique après 2s
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setErreur(extraireMessageErreur(err));
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md">
        {/* Logo / brand */}
        <div className="flex items-center gap-3 mb-8 justify-center">
          <img
            src="/icone_application.png"
            alt="Soft GEDCAP"
            className="h-10 w-10 rounded-xl shadow-card object-contain bg-white ring-1 ring-slate-200/80"
          />
          <div>
            <h1 className="text-base font-bold text-slate-900 tracking-tight leading-none">
              Soft GEDCAP
            </h1>
            <p className="text-[10px] uppercase tracking-wider text-slate-500 mt-1 font-medium">
              GED · GEC · Archivage
            </p>
          </div>
        </div>

        <Card>
          <CardBody className="p-6 space-y-5">
            {verification === 'en_cours' && (
              <div className="text-center py-6">
                <p className="text-sm text-slate-500">Vérification du lien…</p>
              </div>
            )}

            {verification === 'invalide' && (
              <div className="space-y-4">
                <div className="flex items-start gap-3 text-red-700">
                  <AlertCircle className="h-6 w-6 shrink-0 mt-0.5" />
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900">
                      Lien invalide ou expiré
                    </h2>
                    <p className="text-sm text-slate-600 mt-1">
                      Ce lien de réinitialisation n'est plus valable. Demande à
                      un superviseur de t'en envoyer un nouveau.
                    </p>
                  </div>
                </div>
                <Button onClick={() => navigate('/login')} className="w-full">
                  Retour à la connexion
                </Button>
              </div>
            )}

            {verification === 'valide' && succes && (
              <div className="space-y-4">
                <div className="flex items-start gap-3 text-emerald-700">
                  <CheckCircle2 className="h-6 w-6 shrink-0 mt-0.5" />
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900">
                      Mot de passe modifié
                    </h2>
                    <p className="text-sm text-slate-600 mt-1">
                      Tu peux maintenant te connecter avec ton nouveau mot de
                      passe. Redirection automatique…
                    </p>
                  </div>
                </div>
              </div>
            )}

            {verification === 'valide' && !succes && (
              <form onSubmit={onSubmit} className="space-y-4" autoComplete="off">
                <div className="flex items-start gap-3 mb-2">
                  <Lock className="h-5 w-5 text-brand-700 mt-0.5 shrink-0" />
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900 leading-tight">
                      {prenom ? `Bonjour ${prenom}` : 'Nouveau mot de passe'}
                    </h2>
                    <p className="text-sm text-slate-500 mt-0.5">
                      Choisis ton nouveau mot de passe ci-dessous.
                    </p>
                  </div>
                </div>

                <Input
                  label="Nouveau mot de passe"
                  type="password"
                  value={mdp}
                  onChange={(e) => setMdp(e.target.value)}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  placeholder="8 caractères minimum"
                />
                <Input
                  label="Confirmer le mot de passe"
                  type="password"
                  value={confirmation}
                  onChange={(e) => setConfirmation(e.target.value)}
                  required
                  minLength={8}
                  autoComplete="new-password"
                />

                {erreur && (
                  <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
                    {erreur}
                  </div>
                )}

                <Button
                  type="submit"
                  className="w-full"
                  chargement={enCours}
                  disabled={!mdp || !confirmation}
                >
                  Définir mon mot de passe
                </Button>
              </form>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
