# GEDCA — frontend

React 18 + Vite + TypeScript + Tailwind + TanStack Query + React Router.

## Lancer en local

Pré-requis : Node 20+.

```bash
cd frontend
npm install
cp .env.example .env       # si nécessaire, ajuster VITE_API_URL
npm run dev
```

App disponible sur http://localhost:5173. Connectez-vous avec les credentials du seed dev backend (`admin / changeme123` après `python -m scripts.seed_dev`).

## Structure

```
frontend/src/
├── api/                    # Client API typé
│   ├── client.ts           # axios + interceptor (Bearer token, 401 redirect)
│   ├── types.ts            # types alignés avec schemas Pydantic
│   ├── auth.ts             # login/logout
│   ├── agents.ts           # CRUD agents + profil
│   ├── departements.ts
│   ├── structure.ts
│   └── audit.ts
├── auth/                   # Contexte d'authentification
│   ├── AuthContext.tsx     # token + agent en localStorage
│   ├── useAuth.ts
│   └── RequireAuth.tsx     # guard route + check rôle
├── components/
│   ├── ui/                 # mini-design system (Button, Input, Modal, Card, ...)
│   ├── Layout.tsx          # sidebar + header + outlet
│   ├── Sidebar.tsx         # navigation avec entrées conditionnelles au rôle
│   └── Header.tsx          # menu utilisateur (profil + déconnexion)
├── pages/                  # écrans
│   ├── Login.tsx           # écran 0.1
│   ├── Accueil.tsx         # écran 0.2 (placeholder en attente PRD-06)
│   ├── Profil.tsx          # écran 0.4
│   ├── Agents.tsx          # écrans 4.3 + 4.4
│   ├── Departements.tsx    # écran 4.5
│   ├── Structure.tsx       # écran 4.6
│   └── AuditLog.tsx        # consultation audit (superviseur)
├── lib/
│   ├── utils.ts            # cn() Tailwind, formatDate, formatDateTime
│   └── echeance.ts         # port front du backend services/echeances.py
├── App.tsx                 # routing
├── main.tsx                # bootstrap (Query, Router, AuthProvider)
└── index.css               # Tailwind
```

## Tests

```bash
npm test           # tous les tests Vitest
npm run test:watch # mode watch
```

## Build production

```bash
npm run build      # → frontend/dist/
npm run preview    # sert dist/ en local pour vérification
```

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api` | Base URL de l'API backend |
