import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from '../App.jsx'
import { DETALHE, ITEM, irPara, simularApi } from '../testes/apoio.js'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const comItem = (item, { sessao = null, status = 200 } = {}) =>
  simularApi({ sessao, rotas: { [`GET /api/itens/${item.id ?? 'item_1'}`]: () => [status, item] } })

describe('página do item (SCRUM-53, US-04)', () => {
  beforeEach(() => irPara('/itens/item_1'))

  it('mostra tipo, descrição, local, data, situação e onde o objeto está', async () => {
    comItem({ ...DETALHE, localizacao: 'com um setor', setor: 'SecGrad' })
    render(<App />)
    expect(await screen.findByRole('heading', { level: 1, name: 'Garrafa térmica azul' })).toBeTruthy()
    expect(screen.getByText('Achado')).toBeTruthy()
    expect(screen.getByText('Grad 5')).toBeTruthy()
    expect(screen.getByText('aberto')).toBeTruthy()
    expect(screen.getByText('está com um setor: SecGrad')).toBeTruthy()
    expect(document.querySelector('time').getAttribute('dateTime')).toBe(ITEM.data_registro)
  })

  it('perdido não mostra onde o objeto está', async () => {
    comItem({ ...DETALHE, tipo: 'perdido', localizacao: null })
    render(<App />)
    await screen.findByRole('heading', { level: 1 })
    expect(screen.getByText('Perdido')).toBeTruthy()
    expect(screen.queryByText('Onde está agora')).toBeNull()
  })

  it.each([
    ['no local', 'está no local'],
    ['com quem achou', 'está com quem achou'],
    ['caixa do bloco A/E', 'na caixa do bloco A/E'],
    ['devolvido', 'devolvido'],
  ])('localização "%s" aparece como "%s"', async (localizacao, texto) => {
    comItem({ ...DETALHE, localizacao })
    render(<App />)
    await screen.findByRole('heading', { level: 1 })
    expect(screen.getByText(texto)).toBeTruthy()
  })

  it('Dado um item encerrado por declaração de terceiro, mostra "encerrado segundo terceiro"', async () => {
    comItem({ ...DETALHE, situacao: 'encerrado', fonte_encerramento: 'terceiro', localizacao: 'devolvido' })
    render(<App />)
    expect(await screen.findByText('encerrado segundo terceiro')).toBeTruthy()
  })

  it('encerrado pelo autor mostra só "encerrado"', async () => {
    comItem({ ...DETALHE, situacao: 'encerrado', fonte_encerramento: 'confirmação do autor' })
    render(<App />)
    expect(await screen.findByText('encerrado')).toBeTruthy()
    expect(screen.queryByText(/segundo terceiro/)).toBeNull()
  })

  it('item com revisar = true mostra o selo, com a explicação no title', async () => {
    comItem({ ...DETALHE, revisar: true })
    render(<App />)
    const selo = await screen.findByText('revisar')
    expect(selo.getAttribute('title')).toMatch(/confiança média/)
  })

  it('item sem revisar não mostra o selo', async () => {
    comItem(DETALHE)
    render(<App />)
    await screen.findByRole('heading', { level: 1 })
    expect(screen.queryByText('revisar')).toBeNull()
  })

  it('mostra a foto quando há foto_url', async () => {
    comItem({ ...DETALHE, foto_url: '/api/fotos/item_1_1' })
    render(<App />)
    const foto = await screen.findByRole('img')
    expect(foto.getAttribute('src')).toBe('/api/fotos/item_1_1')
    expect(foto.getAttribute('alt')).toMatch(/Garrafa térmica azul/)
  })
})

describe('texto original na página do item (US-04, US-05)', () => {
  beforeEach(() => irPara('/itens/item_1'))

  it('Dado que entrei com a conta do CIn, quando abro um item, vejo o texto original como veio (já mascarado)', async () => {
    const texto = 'Achei uma garrafa.\nQuem for o dono me chama: [TELEFONE MASCARADO]'
    comItem({ ...DETALHE, texto_original: texto }, { sessao: 'Pessoa Fictícia' })
    render(<App />)
    const bloco = await screen.findByRole('region', { name: 'Texto original' })
    // Mostrado do jeito que a API mandou, com as quebras de linha: o site não mascara nem edita nada.
    expect(bloco.querySelector('pre').textContent).toBe(texto)
  })

  it('Dado que não entrei, o texto original não aparece e há o convite para entrar', async () => {
    comItem(DETALHE)
    render(<App />)
    const bloco = await screen.findByRole('region', { name: 'Texto original' })
    expect(bloco.querySelector('pre')).toBeNull()
    expect(bloco.textContent).toMatch(/Entre com a conta do CIn para ler o anúncio completo/)
    const link = within(bloco).getByRole('link', { name: 'Entre com a conta do CIn' })
    expect(link.getAttribute('href')).toBe('/api/auth/google?retorno=%2Fitens%2Fitem_1')
  })

  it('com sessão e texto null (item do site), o bloco não aparece', async () => {
    comItem(DETALHE, { sessao: 'Pessoa Fictícia' })
    render(<App />)
    await screen.findByRole('heading', { level: 1 })
    await waitFor(() => expect(screen.queryByText('Texto original')).toBeNull())
    expect(screen.queryByText(/Entre com a conta do CIn para ler/)).toBeNull()
  })
})

describe('estados da página do item', () => {
  beforeEach(() => irPara('/itens/item_1'))

  it('Dado que um item foi removido, o link direto mostra que ele não está disponível', async () => {
    comItem({ codigo: 'NAO_ENCONTRADO', mensagem: 'x' }, { status: 404 })
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Este anúncio não está disponível' })).toBeTruthy()
    // Mesma tela para oculto e inexistente: nada que diga qual dos dois.
    expect(screen.queryByText(/oculto|removido pelo autor|não existe/i)).toBeNull()
  })

  it('API fora: erro honesto com "Tentar de novo", sem detalhe técnico', async () => {
    let fora = true
    simularApi({ rotas: { 'GET /api/itens/item_1': () => (fora ? [503, { codigo: 'INDISPONIVEL' }] : [200, DETALHE]) } })
    render(<App />)
    const alerta = await screen.findByRole('alert')
    expect(alerta.textContent).not.toMatch(/503|INDISPONIVEL/)
    fora = false
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Garrafa térmica azul' })).toBeTruthy()
  })

  it('mostra "Carregando" enquanto espera a API', async () => {
    simularApi({ rotas: { 'GET /api/itens/item_1': () => [200, DETALHE] } })
    render(<App />)
    expect(screen.getByText('Carregando o anúncio…')).toBeTruthy()
    await screen.findByRole('heading', { level: 1 })
  })
})

describe('do catálogo para o item e de volta', () => {
  it('clicar na descrição abre o item, e "Voltar ao catálogo" mantém os filtros', async () => {
    irPara('/?tipo=achado')
    simularApi({ rotas: { 'GET /api/itens/item_1': () => [200, DETALHE] } })
    render(<App />)
    fireEvent.click(await screen.findByRole('link', { name: 'Garrafa térmica azul' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Garrafa térmica azul' })).toBeTruthy()
    expect(window.location.pathname).toBe('/itens/item_1')
    fireEvent.click(screen.getByRole('link', { name: '← Voltar ao catálogo' }))
    await screen.findByRole('heading', { level: 2, name: 'Garrafa térmica azul' })
    expect(window.location.search).toBe('?tipo=achado')
  })
})

describe('selo e localização no cartão do catálogo', () => {
  beforeEach(() => irPara('/'))

  it('o cartão mostra o selo "revisar", "encerrado segundo terceiro" e a localização do achado', async () => {
    simularApi({
      itens: [{ ...ITEM, revisar: true, situacao: 'encerrado', fonte_encerramento: 'terceiro', localizacao: 'devolvido' }],
    })
    render(<App />)
    const cartao = (await screen.findByText('Garrafa térmica azul')).closest('article')
    expect(within(cartao).getByText('revisar')).toBeTruthy()
    expect(within(cartao).getByText('encerrado segundo terceiro')).toBeTruthy()
    expect(within(cartao).getByText(/devolvido/)).toBeTruthy()
  })
})
