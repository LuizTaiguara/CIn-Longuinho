// Ícones do site, desenhados aqui (sem biblioteca): mesmo traço, mesmo tamanho, sempre decorativos.
// O texto ao lado é que diz o que é; por isso todos saem com aria-hidden.
// Estado nunca depende só da cor: cada situação tem um desenho próprio (anel, meio disco, disco com visto).

const TRACOS = {
  // Tipo do anúncio
  achado: (
    <>
      <path d="M3 12.5V5a2 2 0 0 1 2-2h7.5a2 2 0 0 1 1.4.6l6.5 6.5a2 2 0 0 1 0 2.8l-7.5 7.5a2 2 0 0 1-2.8 0l-6.5-6.5a2 2 0 0 1-.6-1.4Z" />
      <circle cx="8" cy="8" r="1.4" />
    </>
  ),
  perdido: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m20.5 20.5-5.4-5.4" />
    </>
  ),
  // Situação
  aberto: <circle cx="12" cy="12" r="8" />,
  reivindicado: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 4a8 8 0 0 1 0 16Z" fill="currentColor" />
    </>
  ),
  encerrado: (
    <>
      <circle cx="12" cy="12" r="9" fill="currentColor" stroke="none" />
      <path d="m7.8 12.3 2.8 2.8 5.6-5.9" stroke="var(--icone-vazado, #fff)" />
    </>
  ),
  // Apoio
  busca: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m20.5 20.5-5.4-5.4" />
    </>
  ),
  local: (
    <>
      <path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11Z" />
      <circle cx="12" cy="10" r="2.3" />
    </>
  ),
  voltar: <path d="M19 12H5m6-6-6 6 6 6" />,
  avancar: <path d="M5 12h14m-6-6 6 6-6 6" />,
  alerta: (
    <>
      <path d="M12 3.5 2.8 19.5h18.4L12 3.5Z" />
      <path d="M12 10v4.5m0 2.6v.2" />
    </>
  ),
  mais: <path d="M12 5v14M5 12h14" />,
  carta: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3.5 7 8.5 6.5L20.5 7" />
    </>
  ),
  removido: (
    <>
      <path d="M3 3l18 18" />
      <path d="M10.6 5.2A9.6 9.6 0 0 1 12 5c5.5 0 9 7 9 7a15.700 15.700 0 0 1-3 3.800M6.300 6.800C4.100 8.400 3 12 3 12s3.500 7 9 7a9.200 9.200 0 0 0 4-1" />
    </>
  ),
  visto: <path d="m5 12.500 4.500 4.500L19 7" />,
}

export default function Icone({ nome, tamanho = 20, className = '' }) {
  const traco = TRACOS[nome]
  if (!traco) return null
  return (
    <svg
      className={`icone ${className}`.trim()}
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {traco}
    </svg>
  )
}
