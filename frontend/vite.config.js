import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// NOTE: We DO NOT proxy /api here. The frontend talks to
// VITE_API_BASE_URL directly (axios baseURL). This avoids the well-known
// dev-proxy-vs-production drift that hits relative '/api' paths.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
  },
});
