// Mock LOCAL e TEMPORÁRIO da API, só para o `npm run dev` funcionar sem backend.
// Não é o mock oficial: o oficial é a SCRUM-67 (Miguel), publicado junto do contrato.
// Quando ele existir, rode com API_URL apontando para ele e apague esta pasta.
//
// Imita o que o servidor faz em GET /api/itens (busca sem acento e sem maiúscula, filtros,
// paginação), para a tela se comportar como vai se comportar de verdade.
//
// Variáveis para ver os estados da SCRUM-100:
//   MOCK_VAZIO=1  catálogo sem nenhum item (primeira execução)
//   MOCK_FALHA=1  API fora do ar (banco indisponível): responde 503

import { itens as todosOsItens, locais } from './dados.js'

const semAcento = (texto) =>
  String(texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

export function filtrarItens(itens, query) {
  const texto = semAcento(query.get('texto') ?? '').trim()
  const local = query.get('local') ?? ''
  const tipo = query.get('tipo') ?? ''
  const situacao = query.get('situacao') ?? ''

  return itens
    .filter((item) => {
      if (tipo && item.tipo !== tipo) return false
      if (situacao && item.situacao !== situacao) return false
      // Um item que cita vários locais aparece no filtro de qualquer um deles (US-04).
      if (local && !item.local.includes(local)) return false
      if (texto) {
        const alvo = semAcento([item.descricao, ...item.local, item.setor].join(' '))
        if (!texto.split(/\s+/).every((termo) => alvo.includes(termo))) return false
      }
      return true
    })
    .sort((a, b) => b.data_registro.localeCompare(a.data_registro))
}

export function paginar(itens, query) {
  const limite = Math.min(Math.max(Number(query.get('limite')) || 20, 1), 100)
  const totalPaginas = Math.max(Math.ceil(itens.length / limite), 1)
  const pagina = Math.min(Math.max(Number(query.get('pagina')) || 1, 1), totalPaginas)
  return {
    itens: itens.slice((pagina - 1) * limite, pagina * limite),
    paginacao: { pagina_atual: pagina, total_paginas: totalPaginas, total_itens: itens.length, limite },
  }
}

function responder(res, status, corpo) {
  res.statusCode = status
  res.setHeader('Content-Type', 'application/json; charset=utf-8')
  res.end(JSON.stringify(corpo))
}

export function mockLocal() {
  return {
    name: 'mock-local-api',
    configureServer(server) {
      server.middlewares.use('/api', (req, res, next) => {
        if (req.method !== 'GET') return next()
        const url = new URL(req.url, 'http://local')

        if (process.env.MOCK_FALHA) {
          return responder(res, 503, { codigo: 'INDISPONIVEL', mensagem: 'Banco indisponível (simulado).' })
        }
        if (url.pathname === '/itens') {
          const base = process.env.MOCK_VAZIO ? [] : todosOsItens
          return responder(res, 200, paginar(filtrarItens(base, url.searchParams), url.searchParams))
        }
        if (url.pathname === '/locais') return responder(res, 200, locais)
        return responder(res, 404, { codigo: 'NAO_ENCONTRADO', mensagem: 'Rota não existe no mock local.' })
      })
    },
  }
}
