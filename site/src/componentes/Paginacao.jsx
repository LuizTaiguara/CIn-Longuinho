// Paginação do catálogo (US-04: termo genérico traz muitos resultados, paginados).
// A página fica na URL (?pagina=2), junto dos filtros.

export default function Paginacao({ paginacao, onMudar }) {
  const { pagina_atual: atual, total_paginas: total } = paginacao
  if (total <= 1) return null

  return (
    <nav className="paginacao" aria-label="Páginas do catálogo">
      <button type="button" onClick={() => onMudar(atual - 1)} disabled={atual <= 1}>
        ← Mais recentes
      </button>
      <span aria-current="page">
        Página {atual} de {total}
      </span>
      <button type="button" onClick={() => onMudar(atual + 1)} disabled={atual >= total}>
        Mais antigos →
      </button>
    </nav>
  )
}
