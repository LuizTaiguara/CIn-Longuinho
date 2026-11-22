import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { mockLocal } from './mock/servidorLocal.js'

// Sem API_URL, o `npm run dev` serve um mock local em /api (ver "Comandos" no site/AGENTS.md).
// Com API_URL, as chamadas a /api vão para a API de verdade (FastAPI, porta 8000).
const apiUrl = process.env.API_URL

export default defineConfig({
  // Lê o .env da raiz do repositório (o mesmo do compose). Só as variáveis VITE_* vão para o navegador.
  envDir: '..',
  plugins: [react(), ...(apiUrl ? [] : [mockLocal()])],
  server: apiUrl ? { proxy: { '/api': { target: apiUrl, changeOrigin: true } } } : {},
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{js,jsx}', 'mock/**/*.test.js'],
  },
})
