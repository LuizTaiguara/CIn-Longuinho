import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import App from '../App.jsx'
import { DETALHE, ITEM, chamadasA, irPara, simularApi } from '../testes/apoio.js'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

const NOME = 'Pessoa Fictícia'
const EMAIL = {
  para: 'achados-perdidos@cin.ufpe.br',
  assunto: '[AP-K7F3Q2] Achado: Garrafa térmica azul',
  corpo: 'Achado: Garrafa térmica azul\nLocal: Grad 5\nOnde está agora: com quem achou\n\nLink do anúncio: http://localhost:5173/itens/item_101\nCódigo: AP-K7F3Q2',
}

describe('e-mail pronto na confirmação do cadastro (SCRUM-56, US-07)', () => {
  beforeEach(() => irPara('/cadastrar'))

  async function cadastrar(rotaDoEmail = () => [200, EMAIL]) {
    const api = simularApi({
      sessao: NOME,
      rotas: {
        'POST /api/itens': () => [201, { ...DETALHE, id: 'item_101', pode_gerir: true }],
        'GET /api/itens/item_101/email-pronto': rotaDoEmail,
      },
    })
    render(<App />)
    fireEvent.click(await screen.findByLabelText('Achei um objeto'))
    fireEvent.change(screen.getByLabelText('Descrição do objeto'), { target: { value: 'Garrafa térmica azul' } })
    fireEvent.click(await screen.findByLabelText('Grad 5'))
    fireEvent.click(screen.getByLabelText('Comigo (com quem achou)'))
    fireEvent.click(screen.getByRole('button', { name: 'Publicar anúncio' }))
    await screen.findByRole('heading', { name: 'Anúncio publicado' })
    return api
  }

  it('Dado que acabei de cadastrar, a confirmação abre o e-mail pronto para a lista, saindo da minha conta', async () => {
    await cadastrar()
    const mailto = screen.getByRole('link', { name: 'Abrir no meu e-mail' }).getAttribute('href')
    expect(mailto.startsWith('mailto:achados-perdidos@cin.ufpe.br?')).toBe(true)
    const params = new URLSearchParams(mailto.split('?')[1])
    // Assunto padronizado, com o código.
    expect(params.get('subject')).toBe('[AP-K7F3Q2] Achado: Garrafa térmica azul')
    // Corpo com descrição, local, onde está (achado), link e código.
    const corpo = params.get('body')
    for (const trecho of ['Garrafa térmica azul', 'Grad 5', 'Onde está agora', '/itens/item_101', 'AP-K7F3Q2']) {
      expect(corpo).toContain(trecho)
    }
  })

  it('Navegador sem programa de e-mail: há o link da tela de escrever do Gmail', async () => {
    await cadastrar()
    const gmail = new URL(screen.getByRole('link', { name: 'Abrir no Gmail' }).getAttribute('href'))
    expect(gmail.hostname).toBe('mail.google.com')
    expect(gmail.searchParams.get('view')).toBe('cm')
    expect(gmail.searchParams.get('to')).toBe(EMAIL.para)
    expect(gmail.searchParams.get('su')).toBe(EMAIL.assunto)
    expect(gmail.searchParams.get('body')).toBe(EMAIL.corpo)
  })

  it('Se nem o Gmail abrir, o texto está na tela para revisar e copiar', async () => {
    const escrever = vi.fn(() => Promise.resolve())
    vi.stubGlobal('navigator', { ...window.navigator, clipboard: { writeText: escrever } })
    await cadastrar()
    const texto = screen.getByLabelText(/Ou copie o texto/)
    expect(texto.readOnly).toBe(true)
    expect(texto.value).toContain(`Assunto: ${EMAIL.assunto}`)
    expect(texto.value).toContain(EMAIL.corpo)
    fireEvent.click(screen.getByRole('button', { name: 'Copiar' }))
    expect(await screen.findByText('Texto copiado.')).toBeTruthy()
    expect(escrever).toHaveBeenCalledWith(texto.value)
  })

  it('sem área de transferência, o texto fica selecionado para copiar à mão', async () => {
    vi.stubGlobal('navigator', { ...window.navigator, clipboard: undefined })
    await cadastrar()
    fireEvent.click(screen.getByRole('button', { name: 'Copiar' }))
    expect(await screen.findByText(/copie com Ctrl\+C/)).toBeTruthy()
  })

  it('o site não envia nada: nenhuma chamada além de cadastrar e montar o e-mail', async () => {
    const api = await cadastrar()
    const metodos = api.mock.calls.map(([url, init = {}]) => `${init.method ?? 'GET'} ${String(url).split('?')[0]}`)
    expect(metodos.filter((m) => !m.startsWith('GET'))).toEqual(['POST /api/itens'])
  })

  it('se o e-mail pronto não vier, a confirmação aponta "Meus anúncios"', async () => {
    await cadastrar(() => [503, { codigo: 'INDISPONIVEL' }])
    const alerta = screen.getByRole('alert')
    expect(alerta.textContent).toMatch(/Abrir o e-mail de novo/)
    expect(within(alerta).getByRole('link', { name: 'Meus anúncios' }).getAttribute('href')).toBe('/meus-anuncios')
  })
})

describe('"ainda não foi para a lista" em "Meus anúncios" (SCRUM-56, US-07)', () => {
  beforeEach(() => irPara('/meus-anuncios'))

  const doSite = (extras) => ({
    ...ITEM,
    id: 'item_101',
    fora_do_catalogo: false,
    motivo_retencao: null,
    oculto: false,
    origem: 'site',
    codigo: 'AP-K7F3Q2',
    foi_para_a_lista: false,
    ...extras,
  })

  it('Dado que fechei o e-mail sem enviar, o item continua no catálogo, marcado, com o botão para abrir o e-mail de novo', async () => {
    const api = simularApi({
      sessao: NOME,
      rotas: {
        'GET /api/eu/itens': () => [200, [doSite()]],
        'GET /api/itens/item_101/email-pronto': () => [200, EMAIL],
      },
    })
    render(<App />)
    const grupo = await screen.findByRole('region', { name: 'No catálogo' })
    expect(within(grupo).getByText('ainda não foi para a lista')).toBeTruthy()
    fireEvent.click(within(grupo).getByRole('button', { name: 'Abrir o e-mail de novo' }))
    const mailto = (await within(grupo).findByRole('link', { name: 'Abrir no meu e-mail' })).getAttribute('href')
    expect(mailto).toContain(encodeURIComponent('[AP-K7F3Q2]'))
    expect(chamadasA(api, 'GET', '/api/itens/item_101/email-pronto')).toHaveLength(1)
  })

  it('a marcação some quando o worker liga o e-mail ao item (foi_para_a_lista = true)', async () => {
    simularApi({ sessao: NOME, rotas: { 'GET /api/eu/itens': () => [200, [doSite({ foi_para_a_lista: true })]] } })
    render(<App />)
    await screen.findByRole('region', { name: 'No catálogo' })
    expect(screen.queryByText('ainda não foi para a lista')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Abrir o e-mail de novo' })).toBeNull()
  })

  it('item que veio da lista nunca tem a marcação', async () => {
    simularApi({ sessao: NOME, rotas: { 'GET /api/eu/itens': () => [200, [doSite({ origem: 'lista', foi_para_a_lista: true })]] } })
    render(<App />)
    await screen.findByRole('region', { name: 'No catálogo' })
    expect(screen.queryByText('ainda não foi para a lista')).toBeNull()
  })

  it('falha ao montar o e-mail de novo: avisa e deixa tentar outra vez', async () => {
    simularApi({
      sessao: NOME,
      rotas: {
        'GET /api/eu/itens': () => [200, [doSite()]],
        'GET /api/itens/item_101/email-pronto': () => [503, { codigo: 'INDISPONIVEL' }],
      },
    })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Abrir o e-mail de novo' }))
    expect((await screen.findByRole('alert')).textContent).toMatch(/Não foi possível montar o e-mail/)
    expect(screen.getByRole('button', { name: 'Abrir o e-mail de novo' }).disabled).toBe(false)
  })
})
