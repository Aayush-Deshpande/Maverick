/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Layered neutral surfaces — dark theme, Fluent "Mica"/Apple dark-mode style.
        background: '#0e0e10',
        surface: '#161618',
        'surface-card': '#1e1e21',
        'surface-card-hover': '#26262a',
        'surface-border': 'rgba(255,255,255,0.08)',
        'surface-border-strong': 'rgba(255,255,255,0.14)',

        // One confident accent, used sparingly — not a decorative palette.
        accent: '#3B9EFF',
        'accent-dim': 'rgba(59,158,255,0.12)',
        'accent-muted': 'rgba(59,158,255,0.35)',

        // Flat semantic status colors (no neon variants) — still needed for CRITICAL/
        // WARNING/NOMINAL telemetry severity, just rendered calmly instead of glowing.
        critical: '#FF6259',
        'critical-dim': 'rgba(255,98,89,0.12)',
        'critical-muted': 'rgba(255,98,89,0.4)',
        warning: '#FFB340',
        'warning-dim': 'rgba(255,179,64,0.12)',
        'warning-muted': 'rgba(255,179,64,0.4)',
        success: '#4CD273',
        'success-dim': 'rgba(76,210,115,0.12)',
        'success-muted': 'rgba(76,210,115,0.4)',
        'ai-accent': '#C084FC',
        'ai-accent-dim': 'rgba(192,132,252,0.12)',
        'ai-accent-muted': 'rgba(192,132,252,0.4)',
      },
      fontFamily: {
        sans: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        display: ['"Space Grotesk"', '"Archivo Narrow"', '"Archivo"', 'sans-serif'],
        hud: ['"Rajdhani"', '"Space Grotesk"', 'sans-serif'],
        tactical: ['"Rajdhani"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        pixel: ['"Pixel Code"', 'monospace'],
        serif: ['"Times New Roman"', 'Times', 'serif'],
        editorial: ['"Times New Roman"', 'Times', 'serif'],
      },
      boxShadow: {
        // Elevation, not illumination — flat drop shadows instead of colored glows.
        card: '0 1px 2px rgba(0,0,0,0.3), 0 6px 20px rgba(0,0,0,0.25)',
        'card-lg': '0 2px 4px rgba(0,0,0,0.32), 0 12px 32px rgba(0,0,0,0.3)',
        'focus-ring': '0 0 0 3px rgba(59,158,255,0.35)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
