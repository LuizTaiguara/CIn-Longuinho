// Paginação do catálogo (US-04: termo genérico traz muitos resultados, paginados).
// A página fica na URL (?pagina=2), junto dos filtros.

import Icone from './Icone.jsx'

export default function Paginacao({ paginacao, onMudar }) {
  const { pagina_atual: atual, total_paginas: total } = paginacao
  if (total <= 1) return null

  return (
    <nav className="paginacao" aria-label="Páginas do catálogo">
      <button type="button" className="secundario" onClick={() => onMudar(atual - 1)} disabled={atual <= 1}>
        <Icone nome="voltar" tamanho={16} />
        Mais recentes
      </button>
      <span aria-current="page">
        Página {atual} de {total}
      </span>
      <button type="button" className="secundario" onClick={() => onMudar(atual + 1)} disabled={atual >= total}>
        Mais antigos
        <Icone nome="avancar" tamanho={16} />
      </button>
    </nav>
  )
}
