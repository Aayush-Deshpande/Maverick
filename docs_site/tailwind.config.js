/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"DM Mono"', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        serif: ['Newsreader', 'Georgia', 'Cambria', 'serif'],
      },
      colors: {
        surface: {
          ground: '#fafaf9',
          card: '#ffffff',
          subtle: '#f5f5f4',
          muted: '#e7e5e4',
        },
      },
      letterSpacing: {
        technical: '0.08em',
        widest: '0.12em',
      },
    },
  },
  plugins: [],
}
