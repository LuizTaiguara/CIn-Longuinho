import { describe, expect, it } from 'vitest'
import { criarItens } from './dados.js'
import { criarMock, filtrarItens, paginar, retornoSeguro } from './rotas.js'
import { lerFotoDoMultipart, temSessao } from './servidorLocal.js'

const q = (texto = '') => new URLSearchParams(texto)
const publicos = () => criarItens().filter((i) => !i._oculto)

function novoMock(opcoes) {
  const mock = criarMock({ agora: () => '2026-11-15T12:00:00Z', aleatorio: () => 0, ...opcoes })
  const chamar = (metodo, caminho, { sessao = false, corpo = null, foto = null } = {}) => {
    const [rota, busca = ''] = caminho.split('?')
    return mock.tratar({ metodo, caminho: rota, query: q(busca), sessao, corpo, foto })
  }
  return { ...mock, chamar }
}

// Nenhuma resposta do mock pode ter cara de e-mail de pessoa (invariante 1),
// exceto o endereço da própria lista no e-mail pronto.
function semEmailDePessoa(corpo) {
  const texto = JSON.stringify(corpo ?? '').replaceAll('achados-perdidos@cin.ufpe.br', '')
  return !/[\w.+-]+@[\w-]+\.[\w.]+/.test(texto)
}

// Nenhum campo interno do mock (`_autor`, `_texto`, `_oculto`…) sai na resposta.
function semCampoInterno(corpo) {
  return !/"_\w+":/.test(JSON.stringify(corpo ?? ''))
}

describe('mock local de GET /api/itens', () => {
  it('busca sem acento e sem maiúscula', () => {
    expect(filtrarItens(publicos(), q('texto=OCULOS')).map((i) => i.id)).toEqual(['item_0009'])
  })

  it('filtro de local inclui item que cita vários locais', () => {
    const ids = filtrarItens(publicos(), q('local=Grad 4')).map((i) => i.id)
    expect(ids).toContain('item_0005')
    expect(ids).toContain('item_0006')
  })

  it('ordena do mais recente para o mais antigo', () => {
    const datas = filtrarItens(publicos(), q('')).map((i) => i.data_registro)
    expect(datas).toEqual([...datas].sort().reverse())
  })

  it('pagina com os metadados do contrato', () => {
    const itens = publicos()
    const { paginacao } = paginar(itens, q('limite=3&pagina=2'))
    expect(paginacao).toEqual({ pagina_atual: 2, total_paginas: 3, total_itens: itens.length, limite: 3 })
  })

  it('nunca devolve item oculto e não tem campo interno nem e-mail', () => {
    const { corpo } = novoMock().chamar('GET', '/itens?limite=100')
    const ids = corpo.itens.map((i) => i.id)
    expect(ids).not.toContain('item_0004')
    expect(ids).not.toContain('item_0003')
    expect(semCampoInterno(corpo)).toBe(true)
    expect(semEmailDePessoa(corpo)).toBe(true)
  })

  it('todos os campos do ItemResumo vêm sempre, com null quando vazios', () => {
    const { corpo } = novoMock().chamar('GET', '/itens')
    for (const item of corpo.itens) {
      expect(Object.keys(item).sort()).toEqual(
        [
          'data_atualizacao', 'data_registro', 'data_situacao', 'descricao', 'foto_url', 'fonte_encerramento',
          'id', 'local', 'localizacao', 'revisar', 'setor', 'situacao', 'tipo',
        ].sort(),
      )
    }
  })

  it('MOCK_VAZIO e MOCK_FALHA continuam funcionando', () => {
    expect(novoMock({ vazio: true }).chamar('GET', '/itens').corpo.itens).toEqual([])
    expect(novoMock({ falha: true }).chamar('GET', '/itens').status).toBe(503)
  })
})

describe('mock local de GET /api/itens/{id}', () => {
  it('sem sessão: texto original null e pode_gerir false', () => {
    const { status, corpo } = novoMock().chamar('GET', '/itens/item_0012')
    expect(status).toBe(200)
    expect(corpo.texto_original).toBeNull()
    expect(corpo.pode_gerir).toBe(false)
  })

  it('com sessão: texto original mascarado e pode_gerir só no item da sessão', () => {
    const mock = novoMock()
    const meu = mock.chamar('GET', '/itens/item_0012', { sessao: true }).corpo
    const deOutra = mock.chamar('GET', '/itens/item_0011', { sessao: true }).corpo
    expect(meu.pode_gerir).toBe(true)
    expect(meu.texto_original).toMatch(/MASCARADO/)
    expect(deOutra.pode_gerir).toBe(false)
    expect(semEmailDePessoa(meu)).toBe(true)
  })

  it('oculto e inexistente dão o mesmo 404', () => {
    const mock = novoMock()
    expect(mock.chamar('GET', '/itens/item_0004', { sessao: true })).toEqual(mock.chamar('GET', '/itens/nao_existe'))
    expect(mock.chamar('GET', '/itens/item_0004').status).toBe(404)
  })
})

describe('mock local da sessão', () => {
  it('GET /eu: 401 sem cookie e nome sem e-mail com cookie', () => {
    const mock = novoMock()
    expect(mock.chamar('GET', '/eu').status).toBe(401)
    const { corpo } = mock.chamar('GET', '/eu', { sessao: true })
    expect(corpo).toEqual({ autenticado: true, nome: expect.any(String) })
    expect(semEmailDePessoa(corpo)).toBe(true)
  })

  it('GET /auth/google grava o cookie e volta ao retorno', () => {
    const r = novoMock().chamar('GET', '/auth/google?retorno=/itens/item_0012')
    expect(r.status).toBe(302)
    expect(r.cabecalhos.Location).toBe('/itens/item_0012')
    expect(r.cabecalhos['Set-Cookie']).toMatch(/^sessao_mock=1;/)
  })

  it('retorno inválido vai para a página inicial, sem erro', () => {
    expect(retornoSeguro('https://outro.exemplo.invalid/')).toBe('/')
    expect(retornoSeguro('//outro.exemplo.invalid')).toBe('/')
    expect(retornoSeguro(null)).toBe('/')
    expect(retornoSeguro('/cadastrar')).toBe('/cadastrar')
  })

  it('MOCK_LOGIN_FORA devolve à tela de login com o erro de conta de fora', () => {
    const r = novoMock({ loginFora: true }).chamar('GET', '/auth/google?retorno=/')
    expect(r.cabecalhos.Location).toBe('/login?erro=conta_fora_do_cin')
    expect(r.cabecalhos['Set-Cookie']).toBeUndefined()
  })

  it('POST /auth/logout limpa o cookie, e sem sessão dá 401', () => {
    const mock = novoMock()
    expect(mock.chamar('POST', '/auth/logout').status).toBe(401)
    const r = mock.chamar('POST', '/auth/logout', { sessao: true })
    expect(r.status).toBe(204)
    expect(r.cabecalhos['Set-Cookie']).toMatch(/Max-Age=0/)
  })

  it('lê o cookie da sessão do cabeçalho', () => {
    expect(temSessao('outro=2; sessao_mock=1')).toBe(true)
    expect(temSessao('sessao_mock=')).toBe(false)
    expect(temSessao(undefined)).toBe(false)
  })
})

describe('mock local de GET /api/eu/itens', () => {
  it('traz os meus itens, o oculto marcado e a minha retida, nunca a de outra pessoa', () => {
    const { status, corpo } = novoMock().chamar('GET', '/eu/itens', { sessao: true })
    expect(status).toBe(200)
    const porId = Object.fromEntries(corpo.map((i) => [i.id, i]))
    expect(porId.item_0004.oculto).toBe(true)
    expect(porId.item_0004.fora_do_catalogo).toBe(false)
    expect(porId.retida_3.fora_do_catalogo).toBe(true)
    expect(porId.retida_3.motivo_retencao).toBe('direcao_ambigua')
    expect(porId.retida_3.tipo).toBeNull()
    expect(porId.retida_2).toBeUndefined()
    expect(porId.item_0011).toBeUndefined()
    expect(porId.item_0003).toBeUndefined()
    expect(porId.item_0008.foi_para_a_lista).toBe(false)
    expect(semCampoInterno(corpo)).toBe(true)
    expect(semEmailDePessoa(corpo)).toBe(true)
  })

  it('exige sessão', () => {
    expect(novoMock().chamar('GET', '/eu/itens').status).toBe(401)
  })
})

describe('mock local das ações do autor', () => {
  it('PATCH corrige o próprio item; no de outra pessoa dá 403; sem sessão, 401', () => {
    const mock = novoMock()
    const r = mock.chamar('PATCH', '/itens/item_0012', { sessao: true, corpo: { descricao: 'Garrafa azul da Kouda' } })
    expect(r.status).toBe(200)
    expect(r.corpo.descricao).toBe('Garrafa azul da Kouda')
    expect(r.corpo.data_atualizacao).toBe('2026-11-15T12:00:00Z')
    expect(mock.chamar('PATCH', '/itens/item_0011', { sessao: true, corpo: { descricao: 'outra coisa' } }).status).toBe(403)
    expect(mock.chamar('PATCH', '/itens/item_0012', { corpo: { descricao: 'outra coisa' } }).status).toBe(401)
  })

  it('PATCH com outra localização descarta o setor anterior', () => {
    const mock = novoMock()
    mock.chamar('PATCH', '/itens/item_0012', { sessao: true, corpo: { localizacao: 'com um setor', setor: 'SecGrad' } })
    const r = mock.chamar('PATCH', '/itens/item_0012', { sessao: true, corpo: { localizacao: 'no local' } })
    expect(r.corpo.setor).toBeNull()
  })

  it('encerrar leva de aberto direto a encerrado, com a fonte do autor', () => {
    const r = novoMock().chamar('POST', '/itens/item_0012/encerrar', { sessao: true })
    expect(r.corpo.situacao).toBe('encerrado')
    expect(r.corpo.fonte_encerramento).toBe('confirmação do autor')
  })

  it('ocultar tira do catálogo, e o item fica em "Meus anúncios" como oculto', () => {
    const mock = novoMock()
    expect(mock.chamar('POST', '/itens/item_0012/ocultar', { sessao: true }).status).toBe(200)
    expect(mock.chamar('GET', '/itens/item_0012').status).toBe(404)
    const meus = mock.chamar('GET', '/eu/itens', { sessao: true }).corpo
    expect(meus.find((i) => i.id === 'item_0012').oculto).toBe(true)
  })

  it('classificar a retida cria o item; classificar de novo dá 409', () => {
    const mock = novoMock()
    const r = mock.chamar('POST', '/eu/retidas/retida_3/classificar', { sessao: true, corpo: { tipo: 'perdido' } })
    expect(r.status).toBe(201)
    expect(r.corpo.tipo).toBe('perdido')
    expect(mock.chamar('GET', `/itens/${r.corpo.id}`).status).toBe(200)
    expect(mock.chamar('POST', '/eu/retidas/retida_3/classificar', { sessao: true, corpo: { tipo: 'perdido' } }).status).toBe(409)
  })

  it('a retida de outra pessoa dá 404, como se não existisse', () => {
    const r = novoMock().chamar('POST', '/eu/retidas/retida_2/classificar', { sessao: true, corpo: { tipo: 'achado' } })
    expect(r.status).toBe(404)
  })

  it('tipo inválido na classificação dá 422', () => {
    const r = novoMock().chamar('POST', '/eu/retidas/retida_3/classificar', { sessao: true, corpo: { tipo: 'outro' } })
    expect(r.status).toBe(422)
  })
})

describe('mock local do cadastro, da foto e do e-mail pronto', () => {
  const achado = { tipo: 'achado', descricao: 'Guarda-chuva preto', local: ['Grad 5'], localizacao: 'com um setor', setor: 'SecGrad' }

  it('POST /itens cria o item com código AP-XXXXXX e "ainda não foi para a lista"', () => {
    const mock = novoMock()
    const r = mock.chamar('POST', '/itens', { sessao: true, corpo: achado })
    expect(r.status).toBe(201)
    expect(r.corpo.pode_gerir).toBe(true)
    const meu = mock.chamar('GET', '/eu/itens', { sessao: true }).corpo.find((i) => i.id === r.corpo.id)
    expect(meu.codigo).toMatch(/^AP-[A-Z2-7]{6}$/)
    expect(meu.origem).toBe('site')
    expect(meu.foi_para_a_lista).toBe(false)
  })

  it('achado sem localização dá LOCALIZACAO_OBRIGATORIA; perda não guarda localização', () => {
    const mock = novoMock()
    const semLocalizacao = mock.chamar('POST', '/itens', { sessao: true, corpo: { ...achado, localizacao: undefined } })
    expect(semLocalizacao.status).toBe(400)
    expect(semLocalizacao.corpo.codigo).toBe('LOCALIZACAO_OBRIGATORIA')
    const perda = mock.chamar('POST', '/itens', { sessao: true, corpo: { ...achado, tipo: 'perdido' } })
    expect(perda.corpo.localizacao).toBeNull()
    expect(perda.corpo.setor).toBeNull()
  })

  it('POST /itens exige sessão', () => {
    expect(novoMock().chamar('POST', '/itens', { corpo: achado }).status).toBe(401)
  })

  it('foto: aceita PNG, recusa formato e tamanho', () => {
    const mock = novoMock()
    const { id } = mock.chamar('POST', '/itens', { sessao: true, corpo: achado }).corpo
    const png = { tipo: 'image/png', tamanho: 10, dados: Buffer.from('x') }
    const ok = mock.chamar('POST', `/itens/${id}/foto`, { sessao: true, foto: png })
    expect(ok.corpo.foto_url).toMatch(/^\/api\/fotos\//)
    expect(mock.chamar('POST', `/itens/${id}/foto`, { sessao: true, foto: { ...png, tipo: 'image/gif' } }).corpo.codigo).toBe('FOTO_INVALIDA')
    const grande = mock.chamar('POST', `/itens/${id}/foto`, { sessao: true, foto: { ...png, tamanho: 6 * 1024 * 1024 } })
    expect(grande.status).toBe(413)
  })

  it('e-mail pronto tem o código no assunto e o link no corpo; item da lista dá 404', () => {
    const mock = novoMock()
    const { id } = mock.chamar('POST', '/itens', { sessao: true, corpo: achado }).corpo
    const { corpo } = mock.chamar('GET', `/itens/${id}/email-pronto`, { sessao: true })
    expect(corpo.para).toBe('achados-perdidos@cin.ufpe.br')
    expect(corpo.assunto).toMatch(/^\[AP-[A-Z2-7]{6}\] Achado: /)
    expect(corpo.corpo).toContain(`/itens/${id}`)
    expect(corpo.corpo).toContain('Onde está agora')
    expect(mock.chamar('GET', '/itens/item_0012/email-pronto', { sessao: true }).status).toBe(404)
  })
})

describe('mock local do contato', () => {
  it('202 com sessão, 401 sem, 400 fora do tamanho, 502 com MOCK_CONTATO_FALHA', () => {
    const corpo = { mensagem: 'Acho que é minha, posso buscar amanhã?' }
    expect(novoMock().chamar('POST', '/itens/item_0011/contato', { sessao: true, corpo }).status).toBe(202)
    expect(novoMock().chamar('POST', '/itens/item_0011/contato', { corpo }).status).toBe(401)
    expect(novoMock().chamar('POST', '/itens/item_0011/contato', { sessao: true, corpo: { mensagem: 'curta' } }).status).toBe(400)
    expect(novoMock({ contatoFalha: true }).chamar('POST', '/itens/item_0011/contato', { sessao: true, corpo }).status).toBe(502)
  })
})

describe('leitura do multipart da foto', () => {
  it('acha o campo foto e o tipo dele', () => {
    const corpo = Buffer.from(
      '--XyZ\r\nContent-Disposition: form-data; name="foto"; filename="a.png"\r\nContent-Type: image/png\r\n\r\nABC\r\n--XyZ--\r\n',
    )
    const foto = lerFotoDoMultipart(corpo, 'multipart/form-data; boundary=XyZ')
    expect(foto.tipo).toBe('image/png')
    expect(foto.dados.toString()).toBe('ABC')
  })
})
