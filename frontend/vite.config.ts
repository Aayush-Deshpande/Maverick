import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0'
  },
  // `vite preview` (serves the production build - see launch_web_dashboard.bat) does not
  // reliably inherit `server.host`/`server.port` in every Vite version, so this is spelled
  // out explicitly rather than relying on that fallback. Without an explicit host here,
  // `vite preview` binds to localhost only, which breaks the documented mobile-on-wifi flow
  // (a phone hitting the laptop's LAN IP) even though `npm run dev` on the same machine works.
  preview: {
    port: 5173,
    host: '0.0.0.0'
  }
});
