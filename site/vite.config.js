import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { mockLocal } from './mock/servidorLocal.js'

// Sem API_URL, o `npm run dev` serve um mock local em /api (ver "Comandos" no site/AGENTS.md).
// Com API_URL, as chamadas a /api vão para a API de verdade (ou para o mock da SCRUM-67).
const apiUrl = process.env.API_URL

export default defineConfig({
  plugins: [react(), ...(apiUrl ? [] : [mockLocal()])],
  server: apiUrl ? { proxy: { '/api': { target: apiUrl, changeOrigin: true } } } : {},
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{js,jsx}', 'mock/**/*.test.js'],
  },
})
