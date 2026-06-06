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
        // Palette de marque (indigo profond)
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        // Gris légèrement teinté (slate)
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
        card: '0 1px 3px 0 rgb(15 23 42 / 0.04), 0 1px 2px -1px rgb(15 23 42 / 0.04)',
        'card-hover':
          '0 4px 12px -2px rgb(15 23 42 / 0.08), 0 2px 6px -2px rgb(15 23 42 / 0.06)',
        elevated:
          '0 10px 30px -10px rgb(15 23 42 / 0.18), 0 4px 12px -4px rgb(15 23 42 / 0.10)',
        glow: '0 0 0 4px rgb(99 102 241 / 0.10)',
        'inset-soft': 'inset 0 1px 2px 0 rgb(15 23 42 / 0.04)',
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
        'gradient-brand':
          'linear-gradient(135deg, #4f46e5 0%, #6366f1 50%, #818cf8 100%)',
        'gradient-subtle':
          'linear-gradient(180deg, #f8fafc 0%, #ffffff 100%)',
        'gradient-mesh':
          'radial-gradient(at 0% 0%, rgba(99,102,241,0.10) 0px, transparent 40%), radial-gradient(at 100% 50%, rgba(67,56,202,0.06) 0px, transparent 35%)',
      },
    },
  },
  plugins: [],
};
