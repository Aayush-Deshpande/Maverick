/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Warm paper and ink surfaces shared with the editorial overview.
        background: '#f2f1eb',
        surface: '#e8e7df',
        'surface-card': '#f7f6f0',
        'surface-card-hover': '#e9e8e1',
        'surface-border': 'rgba(16, 27, 32, 0.16)',
        'surface-border-strong': 'rgba(16, 27, 32, 0.3)',

        // Editorial rust accent used throughout the overview.
        accent: '#bd4b2b',
        'accent-dim': 'rgba(189, 75, 43, 0.12)',
        'accent-muted': 'rgba(189, 75, 43, 0.38)',

        // Semantic status colors calibrated for aerospace telemetry
        critical: '#a63c32',
        'critical-dim': 'rgba(166, 60, 50, 0.1)',
        'critical-muted': 'rgba(166, 60, 50, 0.36)',
        warning: '#94601d',
        'warning-dim': 'rgba(148, 96, 29, 0.1)',
        'warning-muted': 'rgba(148, 96, 29, 0.36)',
        success: '#36724d',
        'success-dim': 'rgba(54, 114, 77, 0.1)',
        'success-muted': 'rgba(54, 114, 77, 0.34)',
        'ai-accent': '#74518d',
        'ai-accent-dim': 'rgba(116, 81, 141, 0.1)',
        'ai-accent-muted': 'rgba(116, 81, 141, 0.34)',
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
        // Low-contrast paper elevation; no colored glow.
        card: '0 1px 2px rgba(16,27,32,0.06), 0 6px 20px rgba(16,27,32,0.04)',
        'card-lg': '0 2px 4px rgba(16,27,32,0.07), 0 12px 32px rgba(16,27,32,0.05)',
        'focus-ring': '0 0 0 3px rgba(189,75,43,0.2)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'modal-pop': 'modalPop 0.22s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-ring': 'pulseRing 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite',
        'wave-bar-1': 'waveBar 0.8s ease-in-out infinite alternate',
        'wave-bar-2': 'waveBar 0.6s ease-in-out infinite alternate 0.15s',
        'wave-bar-3': 'waveBar 0.9s ease-in-out infinite alternate 0.3s',
        'wave-bar-4': 'waveBar 0.7s ease-in-out infinite alternate 0.1s',
        'wave-bar-5': 'waveBar 0.85s ease-in-out infinite alternate 0.25s',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        modalPop: {
          '0%': { opacity: '0', transform: 'scale(0.97) translateY(4px)' },
          '100%': { opacity: '1', transform: 'scale(1) translateY(0)' },
        },
        pulseRing: {
          '0%': { transform: 'scale(0.95)', opacity: '0.8' },
          '50%': { transform: 'scale(1.15)', opacity: '0.3' },
          '100%': { transform: 'scale(1.3)', opacity: '0' },
        },
        waveBar: {
          '0%': { height: '4px' },
          '100%': { height: '18px' },
        },
      },
    },
  },
  plugins: [],
}
