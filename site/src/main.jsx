import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
// Tektur e Hanken Grotesk servidas pelo próprio site (sem Google Fonts nem CDN).
import './fontes/fontes.css'
import './estilos.css'

createRoot(document.getElementById('raiz')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
