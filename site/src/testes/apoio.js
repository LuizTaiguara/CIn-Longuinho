import { vi } from 'vitest'

export const LOCAIS = [{ nome: 'Grad 1' }, { nome: 'Grad 5' }, { nome: 'Anfiteatro' }]

export const ITEM = {
  id: 'item_1',
  tipo: 'achado',
  revisar: false,
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

// ItemDetalhe: o resumo mais `pode_gerir` e `texto_original`.
export const DETALHE = { ...ITEM, pode_gerir: false, texto_original: null }

export function respostaLista(itens, paginacao = {}) {
  return {
    itens,
    paginacao: { pagina_atual: 1, total_paginas: 1, total_itens: itens.length, limite: 20, ...paginacao },
  }
}

export function json(status, corpo) {
  return Promise.resolve(
    new Response(corpo === null ? null : JSON.stringify(corpo), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

// Simula a API.
// - `itens`: lista, função (url) => lista ou resposta de lista, número de status de erro, ou 'rede'.
// - `locais`: lista ou número de status.
// - `sessao`: null (anônimo, GET /api/eu dá 401) ou o nome da pessoa.
// - `rotas`: { 'METODO /api/caminho': (url, init) => [status, corpo] }, conferidas antes de tudo.
//   O caminho é comparado sem a query.
export function simularApi({ itens = [ITEM], locais = LOCAIS, sessao = null, rotas = {} } = {}) {
  const fetchFalso = vi.fn((url, init = {}) => {
    const endereco = String(url)
    const caminho = endereco.split('?')[0]
    const metodo = (init.method ?? 'GET').toUpperCase()

    const rota = rotas[`${metodo} ${caminho}`]
    if (rota) {
      const resultado = rota(endereco, init)
      if (resultado === 'rede') return Promise.reject(new TypeError('Failed to fetch'))
      return json(...resultado)
    }
    if (metodo === 'GET' && caminho === '/api/eu') {
      return sessao ? json(200, { autenticado: true, nome: sessao }) : json(401, { codigo: 'NAO_AUTENTICADO' })
    }
    if (metodo === 'GET' && caminho === '/api/locais') {
      return typeof locais === 'number' ? json(locais, { codigo: 'ERRO' }) : json(200, locais)
    }
    if (metodo === 'GET' && caminho === '/api/itens') {
      if (itens === 'rede') return Promise.reject(new TypeError('Failed to fetch'))
      if (typeof itens === 'number') return json(itens, { codigo: 'INDISPONIVEL', mensagem: 'fora' })
      const lista = typeof itens === 'function' ? itens(endereco) : itens
      return json(200, Array.isArray(lista) ? respostaLista(lista) : lista)
    }
    return json(404, { codigo: 'NAO_ENCONTRADO' })
  })
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

export function chamadasDeItens(fetchFalso) {
  return fetchFalso.mock.calls
    .map(([url]) => String(url))
    .filter((url) => url === '/api/itens' || url.startsWith('/api/itens?'))
}

// Chamadas feitas a um caminho com um método, com o corpo já lido como JSON quando houver.
export function chamadasA(fetchFalso, metodo, caminho) {
  return fetchFalso.mock.calls
    .filter(([url, init = {}]) => String(url).split('?')[0] === caminho && (init.method ?? 'GET').toUpperCase() === metodo)
    .map(([url, init = {}]) => ({ url: String(url), corpo: typeof init.body === 'string' ? JSON.parse(init.body) : init.body }))
}

// Põe o navegador numa URL antes de renderizar o <App />.
export function irPara(caminho) {
  window.history.replaceState(null, '', caminho)
}
