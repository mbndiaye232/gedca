/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'system-ui',
          'sans-serif',
        ],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        // ──────────────────────────────────────────────────────────────
        //  brand — bleu marine du logo Soft GEDCAP
        //  Couleur d'identité globale : sidebar, headers, CTA primaires,
        //  focus rings, sélection.
        // ──────────────────────────────────────────────────────────────
        brand: {
          50:  '#f3f6fb',
          100: '#e4ebf4',
          200: '#c5d2e5',
          300: '#9ab1cf',
          400: '#6c8bb3',
          500: '#4d6f9c',
          600: '#3c5882',
          700: '#324769',
          800: '#2b3c58',
          900: '#28344a',
          950: '#1a2236',  // ≈ teinte du logo
        },
        // ──────────────────────────────────────────────────────────────
        //  docs — teal premium pour le module Documents (GED)
        //  Évoque le calme, la pérennité, l'archivage numérique.
        // ──────────────────────────────────────────────────────────────
        docs: {
          50:  '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
          950: '#022c22',
        },
        // ──────────────────────────────────────────────────────────────
        //  courriers — ambre/cuivre profond pour le module Courriers (GEC)
        //  Évoque la lettre, le cachet de cire, la correspondance soignée.
        // ──────────────────────────────────────────────────────────────
        courriers: {
          50:  '#fef7ee',
          100: '#fdedd6',
          200: '#fbd6ac',
          300: '#f9b876',
          400: '#f6913e',
          500: '#f37419',
          600: '#e45a10',
          700: '#bd440f',
          800: '#963814',
          900: '#7a3014',
          950: '#421607',
        },
        // ──────────────────────────────────────────────────────────────
        //  archivage — sépia/bronze pour le module Archivage physique
        //  Couleur des dossiers carton, des étiquettes archives.
        // ──────────────────────────────────────────────────────────────
        archivage: {
          50:  '#fbf7f1',
          100: '#f5ebdc',
          200: '#ead4b4',
          300: '#dcb583',
          400: '#cb9255',
          500: '#bd7a3b',
          600: '#a76330',
          700: '#894c2a',
          800: '#703f28',
          900: '#5d3522',
          950: '#341b11',
        },
        // Gris neutres
        surface: {
          DEFAULT: '#ffffff',
          subtle: '#f8fafc',
          muted: '#f1f5f9',
          border: '#e2e8f0',
        },
      },
      boxShadow: {
        // Ombres douces, multi-couches, type Linear/Vercel
        soft: '0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 3px 0 rgb(0 0 0 / 0.05)',
        card: '0 1px 3px 0 rgb(26 34 54 / 0.04), 0 1px 2px -1px rgb(26 34 54 / 0.04)',
        'card-hover':
          '0 8px 24px -8px rgb(26 34 54 / 0.10), 0 4px 8px -2px rgb(26 34 54 / 0.06)',
        elevated:
          '0 16px 40px -12px rgb(26 34 54 / 0.18), 0 6px 16px -4px rgb(26 34 54 / 0.10)',
        // Glow par module — pour les badges / focus rings sémantiques
        'glow-brand': '0 0 0 4px rgb(77 111 156 / 0.18)',
        'glow-docs': '0 0 0 4px rgb(16 185 129 / 0.18)',
        'glow-courriers': '0 0 0 4px rgb(243 116 25 / 0.18)',
        // Premium : ombre plus large et plus douce pour les cartes featured
        premium:
          '0 24px 60px -20px rgb(26 34 54 / 0.18), 0 10px 24px -8px rgb(26 34 54 / 0.10), 0 2px 4px -1px rgb(26 34 54 / 0.04)',
        'inset-soft': 'inset 0 1px 2px 0 rgb(26 34 54 / 0.04)',
      },
      borderRadius: {
        DEFAULT: '0.5rem',
        xl: '0.75rem',
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-right': {
          '0%': { opacity: '0', transform: 'translateX(8px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.96)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        'fade-in': 'fade-in 200ms ease-out',
        'slide-in-right': 'slide-in-right 220ms ease-out',
        'scale-in': 'scale-in 180ms ease-out',
        shimmer: 'shimmer 2.4s linear infinite',
      },
      backgroundImage: {
        // Gradients de marque (bleu marine premium)
        'gradient-brand':
          'linear-gradient(135deg, #1a2236 0%, #28344a 50%, #324769 100%)',
        'gradient-brand-soft':
          'linear-gradient(135deg, #324769 0%, #4d6f9c 100%)',
        'gradient-subtle':
          'linear-gradient(180deg, #f8fafc 0%, #ffffff 100%)',
        // Mesh discret aux teintes marine — pour le volet droit du Login
        'gradient-mesh':
          'radial-gradient(at 0% 0%, rgba(77,111,156,0.18) 0px, transparent 45%), radial-gradient(at 100% 50%, rgba(40,52,74,0.10) 0px, transparent 40%), radial-gradient(at 80% 100%, rgba(243,116,25,0.06) 0px, transparent 40%)',
        // Gradient par module pour les en-têtes / cartes premium
        'gradient-docs':
          'linear-gradient(135deg, #047857 0%, #10b981 100%)',
        'gradient-courriers':
          'linear-gradient(135deg, #bd440f 0%, #f37419 100%)',
        'gradient-archivage':
          'linear-gradient(135deg, #894c2a 0%, #cb9255 100%)',
        // Texture subtile pour la sidebar (très légère teinte marine sur blanc)
        'sidebar-noise':
          'linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)',
      },
    },
  },
  plugins: [],
};
