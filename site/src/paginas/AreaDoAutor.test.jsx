import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from '../App.jsx'
import { lerRascunho } from '../rascunho.js'
import { DETALHE, ITEM, LOCAIS, chamadasA, irPara, simularApi } from '../testes/apoio.js'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

const NOME = 'Pessoa Fictícia'
const MEU = { ...DETALHE, pode_gerir: true, texto_original: 'Achei uma garrafa azul no Grad 5.' }

function doAutor(extras) {
  return {
    ...ITEM,
    fora_do_catalogo: false,
    motivo_retencao: null,
    oculto: false,
    origem: 'lista',
    codigo: null,
    foi_para_a_lista: true,
    ...extras,
  }
}

const RETIDA = doAutor({
  id: 'retida_3',
  tipo: null,
  descricao: 'Alguém viu um guarda-chuva preto?',
  local: [],
  situacao: null,
  localizacao: null,
  fora_do_catalogo: true,
  motivo_retencao: 'direcao_ambigua',
  data_situacao: null,
})
const OCULTO = doAutor({ id: 'item_9', descricao: 'Estojo rosa', oculto: true })
const DA_LISTA = doAutor({ id: 'item_1' })

describe('entrar com a conta do CIn (SCRUM-106, US-15)', () => {
  beforeEach(() => irPara('/itens/item_1?x=1'))

  it('Dado que tenho uma conta do CIn, "Entrar com a conta do CIn" leva ao login da API, com o caminho de volta', async () => {
    simularApi({ rotas: { 'GET /api/itens/item_1': () => [200, DETALHE] } })
    render(<App />)
    const entrar = await screen.findByRole('link', { name: 'Entrar com a conta do CIn' })
    expect(entrar.getAttribute('href')).toBe('/api/auth/google?retorno=%2Fitens%2Fitem_1%3Fx%3D1')
  })

  it('o site não pede nem guarda senha: a tela de login não tem campo de senha', async () => {
    irPara('/login')
    simularApi()
    render(<App />)
    await screen.findByRole('heading', { name: 'Entrar com a conta do CIn' })
    expect(document.querySelector('input[type="password"]')).toBeNull()
    expect(screen.getByText(/não pede nem guarda senha/)).toBeTruthy()
  })

  it('Dado uma conta de outro domínio, a recusa explica que só contas do CIn gerem anúncios, e o catálogo segue aberto', async () => {
    irPara('/login?erro=conta_fora_do_cin')
    simularApi()
    render(<App />)
    expect((await screen.findByRole('alert')).textContent).toBe(
      'Só contas @cin.ufpe.br podem gerir anúncios. O catálogo continua aberto para leitura.',
    )
    fireEvent.click(screen.getByRole('link', { name: 'CIn-Longuinho' }))
    expect(await screen.findByText('Garrafa térmica azul')).toBeTruthy()
  })

  it('Login do Google indisponível: mensagem honesta, e o catálogo segue para leitura', async () => {
    irPara('/login?erro=login_indisponivel')
    simularApi()
    render(<App />)
    expect((await screen.findByRole('alert')).textContent).toMatch(/indisponível agora.*catálogo continua aberto/)
  })

  it.each([
    ['recusado', /O login foi cancelado/],
    ['estado_invalido', /não pôde ser concluído/],
    ['codigo_desconhecido', /Não foi possível entrar agora/],
  ])('erro "%s" da API tem mensagem própria, sem detalhe técnico', async (codigo, mensagem) => {
    irPara(`/login?erro=${codigo}`)
    simularApi()
    render(<App />)
    const alerta = await screen.findByRole('alert')
    expect(alerta.textContent).toMatch(mensagem)
    expect(alerta.textContent).not.toContain(codigo)
  })

  it('com sessão, o cabeçalho mostra "Meus anúncios" e "Sair", e "Sair" encerra a sessão', async () => {
    let logado = true
    const api = simularApi({
      rotas: {
        'GET /api/itens/item_1': () => [200, DETALHE],
        'GET /api/eu': () => (logado ? [200, { autenticado: true, nome: NOME }] : [401, { codigo: 'NAO_AUTENTICADO' }]),
        'POST /api/auth/logout': () => {
          logado = false
          return [204, null]
        },
      },
    })
    render(<App />)
    expect(await screen.findByRole('link', { name: 'Meus anúncios' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))
    expect(await screen.findByRole('link', { name: 'Entrar com a conta do CIn' })).toBeTruthy()
    expect(chamadasA(api, 'POST', '/api/auth/logout')).toHaveLength(1)
    expect(window.location.pathname).toBe('/')
  })

  it('"Meus anúncios" sem sessão manda para o login com o caminho de volta', async () => {
    irPara('/meus-anuncios')
    simularApi()
    render(<App />)
    await screen.findByRole('heading', { name: 'Entrar com a conta do CIn' })
    expect(window.location.pathname).toBe('/login')
    expect(new URLSearchParams(window.location.search).get('retorno')).toBe('/meus-anuncios')
    const botao = screen.getAllByRole('link', { name: 'Entrar com a conta do CIn' }).at(-1)
    expect(botao.getAttribute('href')).toBe('/api/auth/google?retorno=%2Fmeus-anuncios')
  })

  it('retorno de fora do site é ignorado na tela de login', async () => {
    irPara('/login?retorno=https://outro.exemplo.invalid')
    simularApi()
    render(<App />)
    const botao = (await screen.findAllByRole('link', { name: 'Entrar com a conta do CIn' })).at(-1)
    expect(botao.getAttribute('href')).toBe('/api/auth/google?retorno=%2F')
  })
})

describe('"Meus anúncios" (SCRUM-106, US-15)', () => {
  beforeEach(() => irPara('/meus-anuncios'))

  const comMeusItens = (itens, rotas = {}) =>
    simularApi({ sessao: NOME, rotas: { 'GET /api/eu/itens': () => [200, itens], ...rotas } })

  it('Dado que entrei, vejo todos os itens em que sou autor, inclusive os anunciados pela lista', async () => {
    comMeusItens([DA_LISTA])
    render(<App />)
    const grupo = await screen.findByRole('region', { name: 'No catálogo' })
    expect(within(grupo).getByRole('link', { name: 'Garrafa térmica azul' })).toBeTruthy()
  })

  it('Dado uma mensagem minha retida, ela aparece como "não entrou no catálogo", com o motivo', async () => {
    comMeusItens([RETIDA, DA_LISTA])
    render(<App />)
    const grupo = await screen.findByRole('region', { name: 'Não entraram no catálogo' })
    expect(within(grupo).getByText('não entrou no catálogo: não deu para saber se é um achado ou uma perda')).toBeTruthy()
    expect(within(grupo).getByText('Alguém viu um guarda-chuva preto?')).toBeTruthy()
  })

  it('Dado uma retida, "É um perdido" classifica e leva ao item criado', async () => {
    const api = comMeusItens([RETIDA], {
      'POST /api/eu/retidas/retida_3/classificar': () => [201, { ...MEU, id: 'item_77', tipo: 'perdido' }],
      'GET /api/itens/item_77': () => [200, { ...MEU, id: 'item_77', tipo: 'perdido', descricao: 'Guarda-chuva preto' }],
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'É um perdido' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Guarda-chuva preto' })).toBeTruthy()
    expect(window.location.pathname).toBe('/itens/item_77')
    expect(chamadasA(api, 'POST', '/api/eu/retidas/retida_3/classificar')[0].corpo).toEqual({ tipo: 'perdido' })
  })

  it('retida que já virou item (409) avisa e atualiza a lista', async () => {
    let chamadas = 0
    comMeusItens([], {
      'GET /api/eu/itens': () => [200, chamadas++ === 0 ? [RETIDA] : [DA_LISTA]],
      'POST /api/eu/retidas/retida_3/classificar': () => [409, { codigo: 'JA_CLASSIFICADA' }],
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'É um achado' }))
    expect(await screen.findByRole('region', { name: 'No catálogo' })).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'Não entraram no catálogo' })).toBeNull()
  })

  it('o item que removi aparece marcado, sem nenhum botão, e diz que não dá para desfazer', async () => {
    comMeusItens([OCULTO])
    render(<App />)
    const grupo = await screen.findByRole('region', { name: 'Removidos do catálogo' })
    expect(within(grupo).getByText('removido do catálogo')).toBeTruthy()
    expect(within(grupo).getByText('A remoção não pode ser desfeita pelo site.')).toBeTruthy()
    expect(within(grupo).queryByRole('button')).toBeNull()
    expect(within(grupo).queryByRole('link')).toBeNull()
  })

  it('sem anúncios, explica que os da lista aparecem depois de processados', async () => {
    comMeusItens([])
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Você ainda não tem anúncios' })).toBeTruthy()
  })

  it('API fora: erro honesto com "Tentar de novo"', async () => {
    comMeusItens([], { 'GET /api/eu/itens': () => [503, { codigo: 'INDISPONIVEL' }] })
    render(<App />)
    expect((await screen.findByRole('alert')).textContent).toMatch(/Não foi possível carregar/)
  })
})

describe('ações do autor na página do item (SCRUM-106, US-15)', () => {
  beforeEach(() => irPara('/itens/item_1'))

  const comItem = (item, rotas = {}) =>
    simularApi({ sessao: NOME, rotas: { 'GET /api/itens/item_1': () => [200, item], ...rotas } })

  it('Dado o anúncio de outra pessoa, não vejo corrigir, encerrar nem remover', async () => {
    comItem({ ...MEU, pode_gerir: false })
    render(<App />)
    await screen.findByRole('heading', { level: 1 })
    expect(screen.queryByRole('button', { name: 'Corrigir' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Marcar como devolvido' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Remover do catálogo' })).toBeNull()
  })

  it('no meu anúncio aparecem as três ações', async () => {
    comItem(MEU)
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Corrigir' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Marcar como devolvido' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Remover do catálogo' })).toBeTruthy()
  })

  it('Dado meu anúncio, corrijo descrição, local e localização: só o que mudou vai à API, e a tela atualiza', async () => {
    const api = comItem(MEU, {
      'PATCH /api/itens/item_1': (_url, init) => {
        const corpo = JSON.parse(init.body)
        return [200, { ...MEU, ...corpo }]
      },
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Corrigir' }))
    fireEvent.change(screen.getByLabelText('Descrição'), { target: { value: 'Garrafa térmica azul da Kouda' } })
    await waitFor(() => expect(screen.getByLabelText('Anfiteatro')).toBeTruthy())
    fireEvent.click(screen.getByLabelText('Anfiteatro'))
    fireEvent.click(screen.getByLabelText('Entreguei a um setor'))
    fireEvent.change(screen.getByLabelText('Qual setor?'), { target: { value: 'SecGrad' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))

    expect(await screen.findByText('Correção salva.')).toBeTruthy()
    expect(screen.getByRole('heading', { level: 1, name: 'Garrafa térmica azul da Kouda' })).toBeTruthy()
    expect(chamadasA(api, 'PATCH', '/api/itens/item_1')[0].corpo).toEqual({
      descricao: 'Garrafa térmica azul da Kouda',
      local: ['Grad 5', 'Anfiteatro'],
      localizacao: 'com um setor',
      setor: 'SecGrad',
    })
  })

  it('correção sem mudança nenhuma não chama a API', async () => {
    const api = comItem(MEU)
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Corrigir' }))
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Salvar correção' })).toBeNull())
    expect(chamadasA(api, 'PATCH', '/api/itens/item_1')).toHaveLength(0)
  })

  it('descrição curta mostra o erro junto ao campo e nada é enviado', async () => {
    const api = comItem(MEU)
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Corrigir' }))
    fireEvent.change(screen.getByLabelText('Descrição'), { target: { value: 'oi' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))
    expect(await screen.findByText('Descreva o objeto com pelo menos 5 letras.')).toBeTruthy()
    expect(screen.getByLabelText('Descrição').getAttribute('aria-invalid')).toBe('true')
    expect(chamadasA(api, 'PATCH', '/api/itens/item_1')).toHaveLength(0)
  })

  it('perdido não tem o campo de localização na correção', async () => {
    comItem({ ...MEU, tipo: 'perdido', localizacao: null })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Corrigir' }))
    expect(screen.queryByText('Onde o objeto está agora?')).toBeNull()
  })

  it('autor pode corrigir item já encerrado', async () => {
    comItem({ ...MEU, situacao: 'encerrado', fonte_encerramento: 'confirmação do autor' })
    render(<App />)
    expect(await screen.findByRole('button', { name: 'Corrigir' })).toBeTruthy()
  })

  it('Dado meu anúncio aberto, "Marcar como devolvido" pede confirmação e encerra direto', async () => {
    const api = comItem(MEU, {
      'POST /api/itens/item_1/encerrar': () => [200, { ...MEU, situacao: 'encerrado', fonte_encerramento: 'confirmação do autor' }],
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Marcar como devolvido' }))
    expect(chamadasA(api, 'POST', '/api/itens/item_1/encerrar')).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Sim, foi devolvido' }))
    expect(await screen.findByText('Anúncio marcado como devolvido.')).toBeTruthy()
    expect(screen.getByText('encerrado')).toBeTruthy()
    // Encerrado: o botão some.
    expect(screen.queryByRole('button', { name: 'Marcar como devolvido' })).toBeNull()
    expect(chamadasA(api, 'POST', '/api/itens/item_1/encerrar')).toHaveLength(1)
  })

  it('cancelar a confirmação não chama a API', async () => {
    const api = comItem(MEU)
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Marcar como devolvido' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.getByRole('button', { name: 'Marcar como devolvido' })).toBeTruthy()
    expect(chamadasA(api, 'POST', '/api/itens/item_1/encerrar')).toHaveLength(0)
  })

  it('Dado meu anúncio, remover avisa que não dá para desfazer e leva a "Meus anúncios"', async () => {
    const api = comItem(MEU, {
      'POST /api/itens/item_1/ocultar': () => [200, MEU],
      'GET /api/eu/itens': () => [200, [doAutor({ oculto: true })]],
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Remover do catálogo' }))
    expect(screen.getByText(/a remoção não pode ser desfeita pelo site/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Sim, remover do catálogo' }))
    expect(await screen.findByText('Anúncio removido do catálogo.')).toBeTruthy()
    expect(window.location.pathname).toBe('/meus-anuncios')
    expect(await screen.findByRole('region', { name: 'Removidos do catálogo' })).toBeTruthy()
    expect(chamadasA(api, 'POST', '/api/itens/item_1/ocultar')).toHaveLength(1)
  })

  it('se a API recusa com 403, a tela explica e não finge que deu certo', async () => {
    comItem(MEU, { 'POST /api/itens/item_1/encerrar': () => [403, { codigo: 'NAO_AUTORIZADO' }] })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Marcar como devolvido' }))
    fireEvent.click(screen.getByRole('button', { name: 'Sim, foi devolvido' }))
    expect((await screen.findByRole('alert')).textContent).toBe('Só quem anunciou pode mudar este anúncio.')
    expect(screen.getByText('aberto')).toBeTruthy()
  })

  it('Sessão expira no meio da edição: guarda o rascunho, vai ao login e volta ao item com o que foi digitado', async () => {
    let expirada = true
    simularApi({
      rotas: {
        'GET /api/eu': () => [200, { autenticado: true, nome: NOME }],
        'GET /api/itens/item_1': () => [200, MEU],
        'PATCH /api/itens/item_1': () => (expirada ? [401, { codigo: 'NAO_AUTENTICADO' }] : [200, MEU]),
      },
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Corrigir' }))
    fireEvent.change(screen.getByLabelText('Descrição'), { target: { value: 'Texto que não pode se perder' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))

    expect((await screen.findByRole('alert')).textContent).toMatch(/Sua sessão expirou/)
    expect(window.location.pathname).toBe('/login')
    expect(new URLSearchParams(window.location.search).get('retorno')).toBe('/itens/item_1')
    expect(lerRascunho('correcao:item_1').descricao).toBe('Texto que não pode se perder')

    // A pessoa entra de novo e a API a devolve para /itens/item_1.
    cleanup()
    expirada = false
    irPara('/itens/item_1')
    render(<App />)
    expect(await screen.findByText('Recuperamos o que você tinha escrito antes de a sessão expirar.')).toBeTruthy()
    expect(screen.getByLabelText('Descrição').value).toBe('Texto que não pode se perder')
  })

  it('cancelar a correção descarta o rascunho', async () => {
    window.localStorage.setItem('longuinho:rascunho:correcao:item_1', JSON.stringify({
      descricao: 'rascunho antigo',
      locais: { selecionados: ['Grad 5'], temOutro: false, outro: '' },
      localizacao: { localizacao: 'com quem achou', setor: '' },
    }))
    comItem(MEU)
    render(<App />)
    expect((await screen.findByLabelText('Descrição')).value).toBe('rascunho antigo')
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(lerRascunho('correcao:item_1')).toBeNull()
  })
})

describe('campo de locais', () => {
  beforeEach(() => irPara('/itens/item_1'))

  it('"Outro lugar" aceita texto livre, e a lista de locais não bloqueia a correção', async () => {
    const api = simularApi({
      sessao: NOME,
      locais: 503,
      rotas: {
        'GET /api/itens/item_1': () => [200, MEU],
        'PATCH /api/itens/item_1': () => [200, MEU],
      },
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Corrigir' }))
    expect(await screen.findByText(/A lista de locais não carregou/)).toBeTruthy()
    fireEvent.click(screen.getByLabelText('Outro lugar'))
    fireEvent.change(screen.getByLabelText(/Qual\?/), { target: { value: 'Cantina, Biblioteca' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))
    await waitFor(() => expect(chamadasA(api, 'PATCH', '/api/itens/item_1')).toHaveLength(1))
    expect(chamadasA(api, 'PATCH', '/api/itens/item_1')[0].corpo.local).toEqual(['Grad 5', 'Cantina', 'Biblioteca'])
  })

  it('usa os locais de GET /api/locais', async () => {
    simularApi({ sessao: NOME, rotas: { 'GET /api/itens/item_1': () => [200, MEU] } })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Corrigir' }))
    for (const { nome } of LOCAIS) expect(await screen.findByLabelText(nome)).toBeTruthy()
    expect(screen.getByLabelText('Grad 5').checked).toBe(true)
  })
})
