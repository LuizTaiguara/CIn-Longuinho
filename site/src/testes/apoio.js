import { vi } from 'vitest'

export const LOCAIS = [{ nome: 'Grad 1' }, { nome: 'Grad 5' }, { nome: 'Anfiteatro' }]

export const ITEM = {
  id: 'item_1',
  tipo: 'achado',
  descricao: 'Garrafa térmica azul',
  local: ['Grad 5'],
  situacao: 'aberto',
  localizacao: 'com quem achou',
  setor: null,
  foto_url: null,
  data_registro: '2026-11-12T14:32:00Z',
  data_atualizacao: null,
  fonte_encerramento: null,
  data_situacao: '2026-11-12T14:32:00Z',
}

export function respostaLista(itens) {
  return {
    itens,
    paginacao: { pagina_atual: 1, total_paginas: 1, total_itens: itens.length, limite: 20 },
  }
}

function json(status, corpo) {
  return Promise.resolve(new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } }))
}

// Simula a API. `itens` pode ser uma lista ou uma função (url) => lista, ou o número de um status de erro.
export function simularApi({ itens = [ITEM], locais = LOCAIS } = {}) {
  const fetchFalso = vi.fn((url) => {
    const caminho = String(url)
    if (caminho.startsWith('/api/locais')) {
      return typeof locais === 'number' ? json(locais, { codigo: 'ERRO' }) : json(200, locais)
    }
    if (caminho.startsWith('/api/itens')) {
      if (itens === 'rede') return Promise.reject(new TypeError('Failed to fetch'))
      if (typeof itens === 'number') return json(itens, { codigo: 'INDISPONIVEL', mensagem: 'fora' })
      const lista = typeof itens === 'function' ? itens(caminho) : itens
      return json(200, respostaLista(lista))
    }
    return json(404, { codigo: 'NAO_ENCONTRADO' })
  })
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

export function chamadasDeItens(fetchFalso) {
  return fetchFalso.mock.calls.map(([url]) => String(url)).filter((url) => url.startsWith('/api/itens'))
}
