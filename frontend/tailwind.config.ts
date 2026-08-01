import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: '#070a14',
          surface: '#0d1220',
          border: '#1e2740',
          primary: '#00e5ff',
          secondary: '#7c4dff',
          success: '#00e676',
          warning: '#ffb300',
          danger: '#ff5252',
          text: '#e6e9f2',
          muted: '#8a93ab',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'typing': 'typing 1.5s steps(4, end) infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(0, 229, 255, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(0, 229, 255, 0.7)' },
        },
        typing: {
          '0%, 100%': { opacity: '0.2' },
          '50%': { opacity: '1' },
        },
      },
      backgroundImage: {
        'grid-pattern':
          'linear-gradient(rgba(0,229,255,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.05) 1px, transparent 1px)',
      },
      backgroundSize: {
        'grid-pattern': '40px 40px',
      },
    },
  },
  plugins: [],
};

export default config;
