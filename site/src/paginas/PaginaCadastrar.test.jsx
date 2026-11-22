import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from '../App.jsx'
import { lerRascunho } from '../rascunho.js'
import { DETALHE, chamadasA, irPara, simularApi } from '../testes/apoio.js'

beforeEach(() => irPara('/cadastrar'))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

const NOME = 'Pessoa Fictícia'
const CRIADO = { ...DETALHE, id: 'item_101', pode_gerir: true }

function comCadastro(rotas = {}, { sessao = NOME } = {}) {
  return simularApi({
    sessao,
    rotas: {
      'POST /api/itens': (_url, init) => [201, { ...CRIADO, ...JSON.parse(init.body) }],
      'POST /api/itens/item_101/foto': () => [200, { ...CRIADO, foto_url: '/api/fotos/item_101_1' }],
      'GET /api/itens/item_101/email-pronto': () => [
        200,
        { para: 'achados-perdidos@cin.ufpe.br', assunto: '[AP-K7F3Q2] Achado: garrafa', corpo: 'Achado: garrafa' },
      ],
      ...rotas,
    },
  })
}

const foto = (tipo = 'image/png', tamanho = 1024) => {
  const arquivo = new File(['x'], 'foto', { type: tipo })
  Object.defineProperty(arquivo, 'size', { value: tamanho })
  return arquivo
}

async function preencherAchado({ comFoto = null } = {}) {
  fireEvent.click(await screen.findByLabelText('Achei um objeto'))
  fireEvent.change(screen.getByLabelText('Descrição do objeto'), { target: { value: 'Garrafa térmica azul' } })
  fireEvent.click(await screen.findByLabelText('Grad 5'))
  fireEvent.click(screen.getByLabelText('Comigo (com quem achou)'))
  if (comFoto) fireEvent.change(screen.getByLabelText(/Foto \(opcional\)/), { target: { files: [comFoto] } })
}

const publicar = () => fireEvent.click(screen.getByRole('button', { name: 'Publicar anúncio' }))

describe('acesso ao cadastro (SCRUM-55, US-06)', () => {
  it('Dado que não entrei, ao acessar o formulário sou levado a entrar, e volto ao formulário depois', async () => {
    comCadastro({}, { sessao: null })
    render(<App />)
    await screen.findByRole('heading', { name: 'Entrar com a conta do CIn' })
    const botao = screen.getAllByRole('link', { name: 'Entrar com a conta do CIn' }).at(-1)
    expect(botao.getAttribute('href')).toBe('/api/auth/google?retorno=%2Fcadastrar')
  })

  it('o cabeçalho tem "Cadastrar" em todas as telas', async () => {
    irPara('/')
    simularApi()
    render(<App />)
    expect(screen.getByRole('link', { name: 'Cadastrar' }).getAttribute('href')).toBe('/cadastrar')
    await screen.findByText('Garrafa térmica azul')
  })

  it('Dado que entrei, escolho se é um achado ou uma perda', async () => {
    comCadastro()
    render(<App />)
    expect(await screen.findByLabelText('Achei um objeto')).toBeTruthy()
    expect(screen.getByLabelText('Perdi um objeto')).toBeTruthy()
  })
})

describe('cadastro de achado e de perda (SCRUM-55, US-06)', () => {
  it('Dado que achei um objeto: local da lista, descrição, onde deixei e foto; o item é publicado com link na confirmação', async () => {
    const api = comCadastro()
    render(<App />)
    await preencherAchado({ comFoto: foto() })
    publicar()

    expect(await screen.findByRole('heading', { name: 'Anúncio publicado' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'ver o anúncio' }).getAttribute('href')).toBe('/itens/item_101')
    expect(chamadasA(api, 'POST', '/api/itens')[0].corpo).toEqual({
      tipo: 'achado',
      descricao: 'Garrafa térmica azul',
      local: ['Grad 5'],
      localizacao: 'com quem achou',
    })
    const [envioDaFoto] = chamadasA(api, 'POST', '/api/itens/item_101/foto')
    expect(envioDaFoto.corpo.get('foto').type).toBe('image/png')
  })

  it('Dado que perdi: posso marcar mais de um local, e o formulário não pergunta onde o objeto está', async () => {
    const api = comCadastro()
    render(<App />)
    fireEvent.click(await screen.findByLabelText('Perdi um objeto'))
    expect(screen.queryByText('Onde o objeto está agora?')).toBeNull()
    expect(screen.getByText('Onde você perdeu? Pode marcar mais de um.')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Descrição do objeto'), { target: { value: 'Carregador USB-C' } })
    fireEvent.click(await screen.findByLabelText('Grad 1'))
    fireEvent.click(screen.getByLabelText('Anfiteatro'))
    publicar()
    await screen.findByRole('heading', { name: 'Anúncio publicado' })
    const corpo = chamadasA(api, 'POST', '/api/itens')[0].corpo
    expect(corpo).toEqual({ tipo: 'perdido', descricao: 'Carregador USB-C', local: ['Grad 1', 'Anfiteatro'] })
    expect('localizacao' in corpo).toBe(false)
  })

  it('sem foto, não chama a rota da foto', async () => {
    const api = comCadastro()
    render(<App />)
    await preencherAchado()
    publicar()
    await screen.findByRole('heading', { name: 'Anúncio publicado' })
    expect(chamadasA(api, 'POST', '/api/itens/item_101/foto')).toHaveLength(0)
  })

  it('"com um setor" pede o nome do setor e manda junto', async () => {
    const api = comCadastro()
    render(<App />)
    await preencherAchado()
    fireEvent.click(screen.getByLabelText('Entreguei a um setor'))
    fireEvent.change(screen.getByLabelText('Qual setor?'), { target: { value: 'SecGrad' } })
    publicar()
    await screen.findByRole('heading', { name: 'Anúncio publicado' })
    expect(chamadasA(api, 'POST', '/api/itens')[0].corpo).toMatchObject({ localizacao: 'com um setor', setor: 'SecGrad' })
  })

  it('Local fora da lista: "Outro lugar" com campo livre não bloqueia o cadastro', async () => {
    const api = comCadastro()
    render(<App />)
    fireEvent.click(await screen.findByLabelText('Perdi um objeto'))
    fireEvent.change(screen.getByLabelText('Descrição do objeto'), { target: { value: 'Guarda-chuva preto' } })
    fireEvent.click(screen.getByLabelText('Outro lugar'))
    fireEvent.change(screen.getByLabelText(/Qual\?/), { target: { value: 'Cantina' } })
    publicar()
    await screen.findByRole('heading', { name: 'Anúncio publicado' })
    expect(chamadasA(api, 'POST', '/api/itens')[0].corpo.local).toEqual(['Cantina'])
  })
})

describe('validação e falhas do cadastro (SCRUM-55, US-06)', () => {
  it('Dado um campo obrigatório vazio, vejo qual falta junto ao campo, e o que preenchi é preservado', async () => {
    const api = comCadastro()
    render(<App />)
    fireEvent.click(await screen.findByLabelText('Achei um objeto'))
    fireEvent.change(screen.getByLabelText('Descrição do objeto'), { target: { value: 'Garrafa térmica azul' } })
    publicar()
    expect(await screen.findByText('Marque pelo menos um local.')).toBeTruthy()
    expect(screen.getByText('Diga onde o objeto está agora.')).toBeTruthy()
    expect(screen.getByLabelText('Descrição do objeto').value).toBe('Garrafa térmica azul')
    expect(screen.getByLabelText('Achei um objeto').checked).toBe(true)
    expect(chamadasA(api, 'POST', '/api/itens')).toHaveLength(0)
  })

  it('formulário vazio aponta o tipo primeiro e leva o foco até ele', async () => {
    comCadastro()
    render(<App />)
    await screen.findByLabelText('Achei um objeto')
    publicar()
    expect(await screen.findByText('Escolha se você achou ou perdeu o objeto.')).toBeTruthy()
    expect(document.activeElement).toBe(screen.getByLabelText('Achei um objeto'))
  })

  it('400 LOCALIZACAO_OBRIGATORIA da API vira mensagem no campo de localização', async () => {
    comCadastro({ 'POST /api/itens': () => [400, { codigo: 'LOCALIZACAO_OBRIGATORIA', mensagem: 'x' }] })
    render(<App />)
    await preencherAchado()
    publicar()
    expect(await screen.findByText('Diga onde o objeto está agora.')).toBeTruthy()
    expect(screen.getByLabelText('Descrição do objeto').value).toBe('Garrafa térmica azul')
  })

  it('Foto de formato não suportado: explica, não envia nada e preserva o resto', async () => {
    comCadastro()
    render(<App />)
    await preencherAchado({ comFoto: foto('image/gif') })
    expect(screen.getByText('A foto precisa ser JPEG, PNG ou WebP. Escolha outra, ou publique sem foto.')).toBeTruthy()
    expect(screen.getByLabelText('Descrição do objeto').value).toBe('Garrafa térmica azul')
  })

  it('Foto muito grande: explica o limite de 5 MB, e o anúncio pode sair sem ela', async () => {
    const api = comCadastro()
    render(<App />)
    await preencherAchado({ comFoto: foto('image/jpeg', 6 * 1024 * 1024) })
    expect(screen.getByText('A foto passa de 5 MB. Escolha uma menor, ou publique sem foto.')).toBeTruthy()
    publicar()
    // Sem foto válida escolhida, o cadastro segue sem foto.
    await screen.findByRole('heading', { name: 'Anúncio publicado' })
    expect(chamadasA(api, 'POST', '/api/itens/item_101/foto')).toHaveLength(0)
  })

  it('a API recusa a foto (413): o anúncio sai publicado, com aviso de que foi sem foto', async () => {
    comCadastro({ 'POST /api/itens/item_101/foto': () => [413, { codigo: 'FOTO_GRANDE' }] })
    render(<App />)
    await preencherAchado({ comFoto: foto() })
    publicar()
    expect((await screen.findByRole('alert')).textContent).toMatch(/publicado sem foto: a foto passa de 5 MB/)
  })

  it('Envio duplicado (clique duplo): só um item é criado', async () => {
    let liberar
    const api = comCadastro()
    const original = api.getMockImplementation()
    api.mockImplementation((url, init = {}) =>
      String(url) === '/api/itens' && init.method === 'POST'
        ? new Promise((r) => (liberar = () => r(original(url, init))))
        : original(url, init),
    )
    render(<App />)
    await preencherAchado()
    const formulario = screen.getByRole('button', { name: 'Publicar anúncio' }).closest('form')
    fireEvent.submit(formulario)
    fireEvent.submit(formulario)
    fireEvent.click(screen.getByRole('button', { name: 'Publicando…' }))
    expect(screen.getByRole('button', { name: 'Publicando…' }).disabled).toBe(true)
    liberar()
    await screen.findByRole('heading', { name: 'Anúncio publicado' })
    expect(chamadasA(api, 'POST', '/api/itens')).toHaveLength(1)
  })

  it('Banco indisponível no envio: pede para tentar de novo, e nada se perde na tela', async () => {
    comCadastro({ 'POST /api/itens': () => [503, { codigo: 'INDISPONIVEL' }] })
    render(<App />)
    await preencherAchado()
    publicar()
    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível salvar. Tente de novo.')
    expect(screen.getByLabelText('Descrição do objeto').value).toBe('Garrafa térmica azul')
    expect(screen.getByLabelText('Grad 5').checked).toBe(true)
    expect(screen.getByLabelText('Comigo (com quem achou)').checked).toBe(true)
    expect(screen.getByRole('button', { name: 'Publicar anúncio' }).disabled).toBe(false)
  })

  it('sessão expirada no envio: guarda o que foi preenchido, vai ao login e volta ao formulário', async () => {
    comCadastro({ 'POST /api/itens': () => [401, { codigo: 'NAO_AUTENTICADO' }] })
    render(<App />)
    await preencherAchado()
    publicar()
    await waitFor(() => expect(window.location.pathname).toBe('/login'))
    expect(new URLSearchParams(window.location.search).get('retorno')).toBe('/cadastrar')
    expect(lerRascunho('cadastro').descricao).toBe('Garrafa térmica azul')

    cleanup()
    irPara('/cadastrar')
    comCadastro()
    render(<App />)
    expect(await screen.findByText(/Recuperamos o que você tinha preenchido/)).toBeTruthy()
    expect(screen.getByLabelText('Descrição do objeto').value).toBe('Garrafa térmica azul')
    expect(screen.getByLabelText('Achei um objeto').checked).toBe(true)
  })
})
