// Cliente da API REST (contrato em shared/openapi.yaml, prefixo /api).
// O site só conversa com a API: nunca com o banco nem com o worker (site/AGENTS.md).

import { paramsDosFiltros } from '../filtros.js'

const PREFIXO = '/api'

// "Não consegui procurar" é diferente de "nada encontrado" (SCRUM-100).
// Toda falha de rede ou resposta não-OK vira ErroApi, nunca uma lista vazia.
export class ErroApi extends Error {
  constructor(mensagem, { status = null, codigo = null } = {}) {
    super(mensagem)
    this.name = 'ErroApi'
    this.status = status
    this.codigo = codigo
  }
}

async function obterJson(caminho, { signal } = {}) {
  let resposta
  try {
    resposta = await fetch(`${PREFIXO}${caminho}`, { signal, headers: { Accept: 'application/json' } })
  } catch (erro) {
    if (erro.name === 'AbortError') throw erro
    throw new ErroApi('Falha de rede ao falar com a API.')
  }
  if (!resposta.ok) {
    let codigo = null
    try {
      codigo = (await resposta.json())?.codigo ?? null
    } catch {
      // corpo sem JSON: fica só o status
    }
    throw new ErroApi(`A API respondeu ${resposta.status}.`, { status: resposta.status, codigo })
  }
  return resposta.json()
}

export function listarItens(filtros, { pagina = 1, signal } = {}) {
  const params = paramsDosFiltros(filtros)
  if (pagina > 1) params.set('pagina', String(pagina))
  const query = params.toString()
  return obterJson(`/itens${query ? `?${query}` : ''}`, { signal })
}

// GET /api/locais: vocabulário fechado de locais do F-07 (SCRUM-64).
// ATENÇÃO: esta rota ainda não está no contrato (PR #8). Foi pedida ao Miguel em 13/11/2026.
export function listarLocais({ signal } = {}) {
  return obterJson('/locais', { signal })
}
