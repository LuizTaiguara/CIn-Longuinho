// Regras do mock local, sem nada de HTTP: recebe uma requisição já lida e devolve
// { status, corpo, cabecalhos }. Fica separado do servidor para dar para testar sem subir nada.
//
// Imita o contrato inteiro (shared/openapi.yaml, 14 rotas sob /api), inclusive as regras que
// são do servidor: visibilidade (oculto e retida dão 404), autoria (403), texto original só com
// sessão, e nenhum e-mail em resposta nenhuma. É descartável: a API de verdade substitui.

import { NOME_DA_SESSAO, criarItens, criarRetidas, locais } from './dados.js'

export const COOKIE_DA_SESSAO = 'sessao_mock'

const LOCALIZACOES = ['no local', 'com quem achou', 'com um setor', 'caixa do bloco A/E', 'devolvido']
const TIPOS = ['achado', 'perdido']
const FORMATOS_DE_FOTO = ['image/jpeg', 'image/png', 'image/webp']
const LIMITE_DA_FOTO = 5 * 1024 * 1024
const ALFABETO_DO_CODIGO = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'

const semAcento = (texto) =>
  String(texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()

// ---------- catálogo (o que já existia) ----------

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
        // Só descrição e campos extraídos: o texto original nunca entra na busca (US-04).
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

// ---------- formatos de resposta (sem nenhum campo interno) ----------

export function comoResumo(i) {
  return {
    id: i.id,
    tipo: i.tipo,
    revisar: i.revisar,
    descricao: i.descricao,
    local: i.local,
    situacao: i.situacao,
    localizacao: i.localizacao,
    setor: i.setor,
    foto_url: i.foto_url,
    data_registro: i.data_registro,
    data_atualizacao: i.data_atualizacao,
    fonte_encerramento: i.fonte_encerramento,
    data_situacao: i.data_situacao,
  }
}

export function comoDetalhe(i, sessao) {
  return {
    ...comoResumo(i),
    pode_gerir: Boolean(sessao) && i._autor === 'voce',
    // Sem sessão do CIn, o texto original não sai da API (US-05). Com sessão, já vem mascarado.
    texto_original: sessao ? i._texto : null,
  }
}

export function comoItemDoAutor(i) {
  return {
    id: i.id,
    tipo: i.tipo,
    revisar: i.revisar,
    descricao: i.descricao,
    local: i.local,
    situacao: i.situacao,
    localizacao: i.localizacao,
    setor: i.setor,
    fora_do_catalogo: false,
    motivo_retencao: null,
    oculto: i._oculto,
    data_registro: i.data_registro,
    data_situacao: i.data_situacao,
    fonte_encerramento: i.fonte_encerramento,
    origem: i.origem,
    codigo: i.codigo,
    foi_para_a_lista: i.foi_para_a_lista,
    foto_url: i.foto_url,
  }
}

function retidaComoItemDoAutor(r) {
  return {
    id: r.id,
    tipo: null,
    revisar: false,
    descricao: r.descricao,
    local: [],
    situacao: null,
    localizacao: null,
    setor: null,
    fora_do_catalogo: true,
    motivo_retencao: r.motivo_retencao,
    oculto: false,
    data_registro: r.data_registro,
    data_situacao: null,
    fonte_encerramento: null,
    origem: 'lista',
    codigo: null,
    foi_para_a_lista: true,
    foto_url: null,
  }
}

// ---------- apoio ----------

const erro = (status, codigo, mensagem) => ({ status, corpo: { codigo, mensagem } })
const ok = (corpo, status = 200) => ({ status, corpo })

const NAO_AUTENTICADO = erro(401, 'NAO_AUTENTICADO', 'Esta operação exige entrar com a conta do CIn.')
const NAO_AUTORIZADO = erro(403, 'NAO_AUTORIZADO', 'Só quem anunciou pode fazer isso.')
const NAO_ENCONTRADO = erro(404, 'NAO_ENCONTRADO', 'Anúncio não encontrado.')
const invalido = (mensagem) => erro(400, 'PARAMETROS_INVALIDOS', mensagem)

// Mesma regra do contrato: só caminho relativo da própria aplicação. O resto vira a página inicial.
export function retornoSeguro(retorno) {
  if (typeof retorno !== 'string' || !retorno.startsWith('/') || retorno.startsWith('//') || retorno.includes('\\')) {
    return '/'
  }
  return retorno
}

function novoCodigo(aleatorio) {
  let codigo = 'AP-'
  for (let n = 0; n < 6; n += 1) codigo += ALFABETO_DO_CODIGO[Math.floor(aleatorio() * ALFABETO_DO_CODIGO.length)]
  return codigo
}

function locaisValidos(local) {
  return Array.isArray(local) && local.length > 0 && local.every((l) => typeof l === 'string' && l.trim())
}

// ---------- o mock em si ----------

// `opcoes`: { vazio, falha, contatoFalha, loginFora, agora, aleatorio, siteUrl }
export function criarMock(opcoes = {}) {
  const agora = opcoes.agora ?? (() => new Date().toISOString())
  const aleatorio = opcoes.aleatorio ?? Math.random
  const siteUrl = opcoes.siteUrl ?? 'http://localhost:5173'
  const estado = {
    itens: opcoes.vazio ? [] : criarItens(),
    retidas: opcoes.vazio ? [] : criarRetidas(),
    fotos: new Map(),
    proximoId: 100,
  }

  const acharItem = (id) => estado.itens.find((i) => i.id === id && !i._oculto)

  // Ações do autor: 401 sem sessão, 404 se não está visível, 403 se é de outra pessoa.
  function itemDoAutor(id, sessao) {
    if (!sessao) return { falha: NAO_AUTENTICADO }
    const item = acharItem(id)
    if (!item) return { falha: NAO_ENCONTRADO }
    if (item._autor !== 'voce') return { falha: NAO_AUTORIZADO }
    return { item }
  }

  function criarItem(dados, extras) {
    estado.proximoId += 1
    const data = agora()
    const novo = {
      id: `item_0${estado.proximoId}`,
      tipo: dados.tipo,
      revisar: false,
      descricao: dados.descricao,
      local: dados.local,
      situacao: 'aberto',
      localizacao: dados.localizacao ?? null,
      setor: dados.setor ?? null,
      foto_url: null,
      data_registro: data,
      data_atualizacao: null,
      fonte_encerramento: null,
      data_situacao: data,
      origem: 'site',
      codigo: null,
      foi_para_a_lista: true,
      _autor: 'voce',
      _oculto: false,
      _texto: null,
      ...extras,
    }
    estado.itens.unshift(novo)
    return novo
  }

  function emailPronto(item) {
    const rotuloTipo = item.tipo === 'achado' ? 'Achado' : 'Perdido'
    const linhas = [
      `${rotuloTipo}: ${item.descricao}`,
      `Local: ${item.local.join(', ')}`,
    ]
    if (item.tipo === 'achado' && item.localizacao) {
      linhas.push(`Onde está agora: ${item.localizacao}${item.setor ? ` (${item.setor})` : ''}`)
    }
    linhas.push('', `Link do anúncio: ${siteUrl}/itens/${item.id}`, `Código: ${item.codigo}`)
    return {
      para: 'achados-perdidos@cin.ufpe.br',
      assunto: `[${item.codigo}] ${rotuloTipo}: ${item.descricao.slice(0, 60)}`,
      corpo: linhas.join('\n'),
    }
  }

  const rotas = [
    ['GET', /^\/itens$/, ({ query }) => {
      const pagina = paginar(filtrarItens(estado.itens.filter((i) => !i._oculto), query), query)
      return ok({ ...pagina, itens: pagina.itens.map(comoResumo) })
    }],

    ['POST', /^\/itens$/, ({ sessao, corpo }) => {
      if (!sessao) return NAO_AUTENTICADO
      const dados = corpo ?? {}
      if (!TIPOS.includes(dados.tipo)) return invalido('Escolha se é um achado ou uma perda.')
      if (typeof dados.descricao !== 'string' || dados.descricao.trim().length < 5) return invalido('Descrição curta demais.')
      if (!locaisValidos(dados.local)) return invalido('Informe pelo menos um local.')
      if (dados.tipo === 'achado' && !dados.localizacao) {
        return erro(400, 'LOCALIZACAO_OBRIGATORIA', 'Diga onde o objeto está agora.')
      }
      if (dados.localizacao && !LOCALIZACOES.includes(dados.localizacao)) return invalido('Localização fora do vocabulário.')
      const perdido = dados.tipo === 'perdido'
      const novo = criarItem(
        {
          tipo: dados.tipo,
          descricao: dados.descricao.trim(),
          local: dados.local.map((l) => l.trim()),
          localizacao: perdido ? null : dados.localizacao,
          setor: !perdido && dados.localizacao === 'com um setor' ? (dados.setor ?? null) : null,
        },
        { codigo: novoCodigo(aleatorio), foi_para_a_lista: false },
      )
      return ok(comoDetalhe(novo, sessao), 201)
    }],

    ['GET', /^\/locais$/, () => ok(locais)],

    ['GET', /^\/itens\/([^/]+)$/, ({ sessao }, id) => {
      const item = acharItem(id)
      return item ? ok(comoDetalhe(item, sessao)) : NAO_ENCONTRADO
    }],

    ['PATCH', /^\/itens\/([^/]+)$/, ({ sessao, corpo }, id) => {
      const { item, falha } = itemDoAutor(id, sessao)
      if (falha) return falha
      const dados = corpo ?? {}
      if ('descricao' in dados && (typeof dados.descricao !== 'string' || dados.descricao.trim().length < 5)) {
        return invalido('Descrição curta demais.')
      }
      if ('local' in dados && !locaisValidos(dados.local)) return invalido('Informe pelo menos um local.')
      if ('localizacao' in dados) {
        if (item.tipo === 'perdido') return invalido('Perda não tem localização.')
        if (!LOCALIZACOES.includes(dados.localizacao)) return invalido('Localização fora do vocabulário.')
      }
      if ('descricao' in dados) item.descricao = dados.descricao.trim()
      if ('local' in dados) item.local = dados.local.map((l) => l.trim())
      if ('localizacao' in dados) {
        item.localizacao = dados.localizacao
        // Mudou para outro valor: o setor anterior é descartado (contrato).
        item.setor = dados.localizacao === 'com um setor' ? (dados.setor ?? item.setor) : null
      } else if ('setor' in dados && item.localizacao === 'com um setor') {
        item.setor = dados.setor
      }
      item.data_atualizacao = agora()
      return ok(comoDetalhe(item, sessao))
    }],

    ['POST', /^\/itens\/([^/]+)\/encerrar$/, ({ sessao }, id) => {
      const { item, falha } = itemDoAutor(id, sessao)
      if (falha) return falha
      // Já encerrado: a API registra o evento e não muda nada (a situação só avança).
      if (item.situacao !== 'encerrado') {
        item.situacao = 'encerrado'
        item.fonte_encerramento = 'confirmação do autor'
        item.data_situacao = agora()
      }
      return ok(comoDetalhe(item, sessao))
    }],

    ['POST', /^\/itens\/([^/]+)\/ocultar$/, ({ sessao }, id) => {
      const { item, falha } = itemDoAutor(id, sessao)
      if (falha) return falha
      item._oculto = true
      return ok(comoDetalhe(item, sessao))
    }],

    ['GET', /^\/itens\/([^/]+)\/email-pronto$/, ({ sessao }, id) => {
      const { item, falha } = itemDoAutor(id, sessao)
      if (falha) return falha
      if (item.origem !== 'site') return NAO_ENCONTRADO
      return ok(emailPronto(item))
    }],

    ['POST', /^\/itens\/([^/]+)\/foto$/, ({ sessao, foto }, id) => {
      const { item, falha } = itemDoAutor(id, sessao)
      if (falha) return falha
      if (!foto) return erro(400, 'FOTO_INVALIDA', 'Envie a foto no campo "foto".')
      if (!FORMATOS_DE_FOTO.includes(foto.tipo)) return erro(400, 'FOTO_INVALIDA', 'A foto precisa ser JPEG, PNG ou WebP.')
      if (foto.tamanho > LIMITE_DA_FOTO) return erro(413, 'FOTO_GRANDE', 'A foto passa de 5 MB.')
      const nome = `${item.id}_${estado.fotos.size + 1}`
      estado.fotos.set(nome, foto)
      item.foto_url = `/api/fotos/${nome}`
      return ok(comoDetalhe(item, sessao))
    }],

    ['GET', /^\/fotos\/([^/]+)$/, (_req, nome) => {
      const foto = estado.fotos.get(nome)
      if (!foto) return NAO_ENCONTRADO
      return { status: 200, binario: foto.dados, cabecalhos: { 'Content-Type': foto.tipo } }
    }],

    ['POST', /^\/itens\/([^/]+)\/contato$/, ({ sessao, corpo }, id) => {
      if (!sessao) return NAO_AUTENTICADO
      if (!acharItem(id)) return NAO_ENCONTRADO
      const mensagem = corpo?.mensagem
      if (typeof mensagem !== 'string' || mensagem.trim().length < 10 || mensagem.length > 2000) {
        return invalido('A mensagem precisa ter entre 10 e 2000 caracteres.')
      }
      if (opcoes.contatoFalha) return erro(502, 'ENVIO_FALHOU', 'Não foi possível enviar (simulado).')
      // O mock não envia nada. A API envia pela conta do projeto, com o e-mail da sessão no Reply-To.
      return { status: 202, corpo: null }
    }],

    ['GET', /^\/eu$/, ({ sessao }) => (sessao ? ok({ autenticado: true, nome: NOME_DA_SESSAO }) : NAO_AUTENTICADO)],

    ['GET', /^\/eu\/itens$/, ({ sessao }) => {
      if (!sessao) return NAO_AUTENTICADO
      const meus = estado.itens.filter((i) => i._autor === 'voce').map(comoItemDoAutor)
      const retidas = estado.retidas.filter((r) => r._autor === 'voce' && !r._classificada).map(retidaComoItemDoAutor)
      return ok([...retidas, ...meus].sort((a, b) => b.data_registro.localeCompare(a.data_registro)))
    }],

    ['POST', /^\/eu\/retidas\/([^/]+)\/classificar$/, ({ sessao, corpo }, id) => {
      if (!sessao) return NAO_AUTENTICADO
      // Retida de outra pessoa dá 404, como se não existisse (US-15).
      const retida = estado.retidas.find((r) => r.id === id && r._autor === 'voce')
      if (!retida) return NAO_ENCONTRADO
      if (retida._classificada) return erro(409, 'JA_CLASSIFICADA', 'Essa mensagem já virou anúncio.')
      if (!TIPOS.includes(corpo?.tipo)) return erro(422, 'PARAMETROS_INVALIDOS', 'Tipo inválido.')
      retida._classificada = true
      const novo = criarItem(
        { tipo: corpo.tipo, descricao: retida.descricao, local: [], localizacao: null },
        { origem: 'lista', data_registro: retida.data_registro, _texto: retida.descricao },
      )
      return ok(comoDetalhe(novo, sessao), 201)
    }],

    ['GET', /^\/auth\/google$/, ({ query }) => {
      if (opcoes.loginFora) {
        return { status: 302, corpo: null, cabecalhos: { Location: '/login?erro=conta_fora_do_cin' } }
      }
      return {
        status: 302,
        corpo: null,
        cabecalhos: {
          'Set-Cookie': `${COOKIE_DA_SESSAO}=1; Path=/; HttpOnly; SameSite=Lax`,
          Location: retornoSeguro(query.get('retorno')),
        },
      }
    }],

    ['POST', /^\/auth\/logout$/, ({ sessao }) => {
      if (!sessao) return NAO_AUTENTICADO
      return { status: 204, corpo: null, cabecalhos: { 'Set-Cookie': `${COOKIE_DA_SESSAO}=; Max-Age=0; Path=/` } }
    }],
  ]

  // `req`: { metodo, caminho (sem /api), query (URLSearchParams), sessao (bool), corpo, foto }
  function tratar(req) {
    if (opcoes.falha) return erro(503, 'INDISPONIVEL', 'Banco indisponível (simulado).')
    for (const [metodo, padrao, acao] of rotas) {
      const achou = req.caminho.match(padrao)
      if (achou && metodo === req.metodo) return acao(req, ...achou.slice(1).map(decodeURIComponent))
    }
    return erro(404, 'NAO_ENCONTRADO', 'Rota não existe no mock local.')
  }

  return { tratar, estado }
}
