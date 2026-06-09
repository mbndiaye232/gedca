import { useEffect, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Mail, Send, ShieldCheck } from 'lucide-react';
import {
  lireParametresSmtp,
  majParametresSmtp,
  testerSmtp,
  type ParametresSmtpLecture,
  type ParametresSmtpMiseAJour,
} from '@/api/parametresSmtp';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardBody, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { extraireMessageErreur } from '@/api/client';

/**
 * Page Paramètres mail (superviseur).
 *
 * Configure le SMTP qui sera utilisé pour toutes les notifications du
 * tenant : nouveau courrier, imputation, demande/validation, mise en
 * copie, alertes retard, lien de réinitialisation de mot de passe, etc.
 *
 * Sécurité :
 * - Le mot de passe SMTP est chiffré côté backend (AES-256-GCM).
 * - Il n'est jamais renvoyé à l'UI — on affiche juste un badge
 *   « Mot de passe configuré » s'il est défini.
 * - Pour le changer : saisir une nouvelle valeur. Pour le conserver :
 *   laisser le champ vide.
 */
export default function ParametresMail() {
  const queryClient = useQueryClient();

  const { data: config, isLoading } = useQuery({
    queryKey: ['parametres-smtp'],
    queryFn: lireParametresSmtp,
  });

  // États du formulaire — initialisés depuis config quand elle arrive
  const [host, setHost] = useState('');
  const [port, setPort] = useState<string>('587');
  const [user, setUser] = useState('');
  const [password, setPassword] = useState('');
  const [from, setFrom] = useState('');
  const [useTls, setUseTls] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState(false);

  useEffect(() => {
    if (config) {
      setHost(config.smtp_host ?? '');
      setPort(config.smtp_port?.toString() ?? '587');
      setUser(config.smtp_user ?? '');
      setFrom(config.smtp_from ?? '');
      setUseTls(config.smtp_use_tls);
      // password volontairement non-rempli — l'UI distingue
      // "défini en base" via le badge, et l'utilisateur ne saisit
      // une valeur que s'il veut le modifier
    }
  }, [config]);

  const sauvegarde = useMutation({
    mutationFn: () => {
      const body: ParametresSmtpMiseAJour = {
        smtp_host: host || null,
        smtp_port: port ? Number(port) : null,
        smtp_user: user || null,
        smtp_from: from || null,
        smtp_use_tls: useTls,
      };
      // N'envoie le password QUE s'il a été saisi (sinon le backend
      // conserve l'existant). Une chaîne vide effacerait le password
      // — c'est cohérent avec la sémantique backend.
      if (password.length > 0) {
        body.smtp_password = password;
      }
      return majParametresSmtp(body);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['parametres-smtp'] });
      setPassword(''); // toujours vider après save
      setSucces(true);
      setErreur(null);
      setTimeout(() => setSucces(false), 4000);
    },
    onError: (err) => {
      setErreur(extraireMessageErreur(err));
      setSucces(false);
    },
  });

  const test = useMutation({
    mutationFn: () => testerSmtp(),
    onSuccess: (data) => {
      if (data.envoye) {
        alert(
          `✅ Email de test envoyé à ${data.destinataire}.\n\n` +
            `Vérifie ta boîte de réception (et le dossier spam) pour confirmer la bonne réception.`,
        );
      } else {
        alert(
          `❌ Échec de l'envoi du test.\n\n` +
            `Cause : ${data.erreur ?? 'inconnue'}\n\n` +
            `Vérifie les identifiants, le port et l'option TLS.`,
        );
      }
    },
    onError: (err) => alert(extraireMessageErreur(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErreur(null);
    setSucces(false);
    sauvegarde.mutate();
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <PageHeader
        titre="Paramètres mail"
        sousTitre="Configure le serveur SMTP utilisé pour envoyer toutes les notifications du tenant."
      />

      {/* État courant */}
      <EtatBadge config={config} isLoading={isLoading} />

      {/* Formulaire */}
      <form onSubmit={onSubmit} className="space-y-6" autoComplete="off">
        <Card>
          <CardHeader>
            <CardTitle>Serveur SMTP</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <Input
                  label="Hôte"
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  placeholder="ex: smtp.gmail.com"
                  required
                />
              </div>
              <Input
                label="Port"
                type="number"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                placeholder="587"
                min={1}
                max={65535}
              />
            </div>

            <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={useTls}
                onChange={(e) => setUseTls(e.target.checked)}
                className="rounded border-slate-300"
              />
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              Activer le chiffrement TLS (STARTTLS sur port 587, recommandé)
            </label>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Authentification</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            {/* Honey-pot anti-autocomplete Chrome */}
            <input
              type="text"
              name="fake-username"
              autoComplete="username"
              tabIndex={-1}
              aria-hidden="true"
              style={{ position: 'absolute', left: '-9999px', width: 0, height: 0 }}
              readOnly
            />
            <input
              type="password"
              name="fake-password"
              autoComplete="current-password"
              tabIndex={-1}
              aria-hidden="true"
              style={{ position: 'absolute', left: '-9999px', width: 0, height: 0 }}
              readOnly
            />

            <Input
              label="Utilisateur"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              placeholder="adresse@exemple.com"
              autoComplete="new-password"
              name="smtp-user-input"
              required
            />
            <Input
              label={
                config?.password_defini
                  ? 'Nouveau mot de passe (laisser vide pour conserver)'
                  : 'Mot de passe'
              }
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={
                config?.password_defini
                  ? '••••••••  (déjà configuré)'
                  : 'Saisir le mot de passe SMTP'
              }
              autoComplete="new-password"
              name="smtp-password-input"
            />
            <Input
              label="Adresse d'expédition (From)"
              type="email"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              placeholder="noreply@exemple.com (par défaut : l'utilisateur)"
            />
          </CardBody>
        </Card>

        {/* Erreurs + succès */}
        {erreur && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            {erreur}
          </div>
        )}
        {succes && (
          <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-800 flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
            Configuration enregistrée. Tu peux maintenant tester l'envoi avec le bouton ci-dessous.
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between gap-3">
          <Button
            type="button"
            variante="secondaire"
            onClick={() => test.mutate()}
            chargement={test.isPending}
            disabled={!config?.password_defini && password.length === 0}
            title={
              !config?.password_defini && password.length === 0
                ? "Renseigne d'abord les identifiants et enregistre"
                : "Envoie un email test à ton adresse"
            }
          >
            <Send className="h-4 w-4" /> Tester l'envoi
          </Button>
          <Button type="submit" chargement={sauvegarde.isPending}>
            Enregistrer la configuration
          </Button>
        </div>
      </form>

      {/* Aide */}
      <Card>
        <CardHeader>
          <CardTitle>Configurations courantes</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <ProviderCard
              nom="Gmail (mot de passe d'application)"
              host="smtp.gmail.com"
              port={587}
              tls
              note="Active la double authentification puis génère un mot de passe d'application (myaccount.google.com/apppasswords)."
            />
            <ProviderCard
              nom="Microsoft 365 / Outlook"
              host="smtp.office365.com"
              port={587}
              tls
              note="L'utilisateur doit avoir l'authentification de base activée par l'admin du tenant Microsoft."
            />
            <ProviderCard
              nom="OVH"
              host="ssl0.ovh.net"
              port={587}
              tls
              note="Utilise l'adresse de la boîte comme nom d'utilisateur."
            />
            <ProviderCard
              nom="Mailpit (dev local)"
              host="localhost"
              port={1025}
              tls={false}
              note="Pour tester en dev sans envoyer de vrais emails. Run : docker run -p 1025:1025 -p 8025:8025 axllent/mailpit"
            />
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

function EtatBadge({
  config,
  isLoading,
}: {
  config: ParametresSmtpLecture | undefined;
  isLoading: boolean;
}) {
  if (isLoading) return null;
  const configure = config && config.smtp_host && config.smtp_user && config.password_defini;
  return (
    <Card>
      <CardBody className="p-4">
        <div className="flex items-center gap-3">
          <div
            className={
              configure
                ? 'h-10 w-10 rounded-xl bg-emerald-50 ring-1 ring-emerald-200 flex items-center justify-center'
                : 'h-10 w-10 rounded-xl bg-amber-50 ring-1 ring-amber-200 flex items-center justify-center'
            }
          >
            <Mail
              className={
                configure ? 'h-5 w-5 text-emerald-700' : 'h-5 w-5 text-amber-700'
              }
            />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-slate-900">
                {configure ? 'SMTP configuré' : 'SMTP non configuré'}
              </p>
              {configure ? (
                <Badge variante="succes" pastille>
                  Actif
                </Badge>
              ) : (
                <Badge variante="attention" pastille>
                  À configurer
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {configure
                ? `Serveur : ${config.smtp_host}:${config.smtp_port ?? 587} — utilisateur : ${config.smtp_user}`
                : "Sans configuration SMTP, aucune notification ne sera envoyée (création de courrier, imputation, réinitialisation de mot de passe, etc.). Les actions métier fonctionnent normalement, juste pas d'email."}
            </p>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function ProviderCard({
  nom,
  host,
  port,
  tls,
  note,
}: {
  nom: string;
  host: string;
  port: number;
  tls: boolean;
  note: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 space-y-1">
      <p className="text-sm font-medium text-slate-900">{nom}</p>
      <p className="text-xs text-slate-500 font-mono">
        {host}:{port} {tls && '(TLS)'}
      </p>
      <p className="text-xs text-slate-600">{note}</p>
    </div>
  );
}
