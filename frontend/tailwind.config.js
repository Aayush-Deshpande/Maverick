/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Layered neutral surfaces — deep aerospace dark palette matching the landing page
        background: '#0e151b',
        surface: '#131e26',
        'surface-card': '#17242c',
        'surface-card-hover': '#1e2f38',
        'surface-border': 'rgba(208, 210, 203, 0.14)',
        'surface-border-strong': 'rgba(208, 210, 203, 0.28)',

        // Signature aerospace orange accent (matching landing page --ani-accent #b84327 / #d67658)
        accent: '#d67658',
        'accent-dim': 'rgba(214, 118, 88, 0.16)',
        'accent-muted': 'rgba(214, 118, 88, 0.4)',

        // Semantic status colors calibrated for aerospace telemetry
        critical: '#e05244',
        'critical-dim': 'rgba(224, 82, 68, 0.15)',
        'critical-muted': 'rgba(224, 82, 68, 0.45)',
        warning: '#e5983b',
        'warning-dim': 'rgba(229, 152, 59, 0.15)',
        'warning-muted': 'rgba(229, 152, 59, 0.45)',
        success: '#2fb36d',
        'success-dim': 'rgba(47, 179, 109, 0.15)',
        'success-muted': 'rgba(47, 179, 109, 0.45)',
        'ai-accent': '#c084fc',
        'ai-accent-dim': 'rgba(192, 132, 252, 0.14)',
        'ai-accent-muted': 'rgba(192, 132, 252, 0.42)',
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
