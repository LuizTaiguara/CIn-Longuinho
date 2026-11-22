// Cliente da API REST (contrato em shared/openapi.yaml, prefixo /api).
// O site só conversa com a API: nunca com o banco nem com o worker (site/AGENTS.md).
// A sessão é o cookie HTTP-only que a API grava; o fetch o manda sozinho (mesma origem).

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

// `corpo`: objeto (vai como JSON) ou FormData (vai como multipart). Respostas sem corpo
// (202, 204) devolvem null.
async function requisitar(caminho, { metodo = 'GET', corpo, signal } = {}) {
  const opcoes = { method: metodo, signal, headers: { Accept: 'application/json' } }
  if (corpo instanceof FormData) {
    opcoes.body = corpo
  } else if (corpo !== undefined) {
    opcoes.headers['Content-Type'] = 'application/json'
    opcoes.body = JSON.stringify(corpo)
  }

  let resposta
  try {
    resposta = await fetch(`${PREFIXO}${caminho}`, opcoes)
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
  if (resposta.status === 202 || resposta.status === 204) return null
  const texto = await resposta.text()
  return texto ? JSON.parse(texto) : null
}

const comId = (id) => encodeURIComponent(id)

export function listarItens(filtros, { pagina = 1, signal } = {}) {
  const params = paramsDosFiltros(filtros)
  if (pagina > 1) params.set('pagina', String(pagina))
  const query = params.toString()
  return requisitar(`/itens${query ? `?${query}` : ''}`, { signal })
}

// GET /api/locais: vocabulário fechado de locais do F-07 (SCRUM-64).
export function listarLocais({ signal } = {}) {
  return requisitar('/locais', { signal })
}

// GET /api/itens/{id}: 404 para item oculto, retido ou inexistente, sem distinguir.
export function obterItem(id, { signal } = {}) {
  return requisitar(`/itens/${comId(id)}`, { signal })
}

// GET /api/eu: 401 quer dizer só "ninguém entrou". Não é erro de tela.
export function obterSessao({ signal } = {}) {
  return requisitar('/eu', { signal })
}

// O login é todo da API: o site só manda a pessoa para lá, com o caminho para voltar.
// O site nunca fala com o Google.
export function linkDeLogin(retorno = '/') {
  return `${PREFIXO}/auth/google?retorno=${encodeURIComponent(retorno)}`
}

// POST /api/auth/logout. 401 (já não havia sessão) também conta como "saiu".
export async function sair() {
  try {
    await requisitar('/auth/logout', { metodo: 'POST' })
  } catch (erro) {
    if (erro.status !== 401) throw erro
  }
}

// ---------- área do autor (US-15). Quem nega é a API (401/403); o site só esconde botões. ----------

export function listarMeusItens({ signal } = {}) {
  return requisitar('/eu/itens', { signal })
}

export function classificarRetida(id, tipo) {
  return requisitar(`/eu/retidas/${comId(id)}/classificar`, { metodo: 'POST', corpo: { tipo } })
}

// Só descricao, local, localizacao e setor (AtualizarItemRequisicao).
export function corrigirItem(id, mudancas) {
  return requisitar(`/itens/${comId(id)}`, { metodo: 'PATCH', corpo: mudancas })
}

export function encerrarItem(id) {
  return requisitar(`/itens/${comId(id)}/encerrar`, { metodo: 'POST' })
}

export function ocultarItem(id) {
  return requisitar(`/itens/${comId(id)}/ocultar`, { metodo: 'POST' })
}

// ---------- contato com quem anunciou (US-05) ----------

// POST /api/itens/{id}/contato. A API manda pela conta do projeto, com o e-mail da sessão no
// Reply-To. O site nunca vê, pede nem guarda endereço nenhum. 202 = aceita.
export function contatarAutor(id, mensagem) {
  return requisitar(`/itens/${comId(id)}/contato`, { metodo: 'POST', corpo: { mensagem } })
}

// ---------- cadastro pelo site e e-mail pronto (US-06, US-07) ----------

// POST /api/itens. Achado precisa de `localizacao`; perdido não manda (contrato).
export function cadastrarItem(dados) {
  return requisitar('/itens', { metodo: 'POST', corpo: dados })
}

// POST /api/itens/{id}/foto, multipart com o campo `foto`.
export function enviarFoto(id, arquivo) {
  const formulario = new FormData()
  formulario.append('foto', arquivo)
  return requisitar(`/itens/${comId(id)}/foto`, { metodo: 'POST', corpo: formulario })
}

// GET /api/itens/{id}/email-pronto: { para, assunto, corpo }. Só para item cadastrado pelo site.
export function obterEmailPronto(id, { signal } = {}) {
  return requisitar(`/itens/${comId(id)}/email-pronto`, { signal })
}
