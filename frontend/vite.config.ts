import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// VITE_BASE_PATH controla o subpath do deploy.
// Exemplos:
//   Sem subpath (padrao):  VITE_BASE_PATH=/       → https://mcp.dominio.com/
//   Com subpath:           VITE_BASE_PATH=/otrs/   → https://mcp.dominio.com/otrs/
const basePath = process.env.VITE_BASE_PATH || '/'

export default defineConfig({
  base: basePath,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
  },
})
