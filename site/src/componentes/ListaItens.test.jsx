import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from '../App.jsx'
import { ITEM, chamadasDeItens, irPara, respostaLista, simularApi } from '../testes/apoio.js'

beforeEach(() => irPara('/'))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const MAIS_NOVO = { ...ITEM, id: 'item_2', descricao: 'Carregador USB-C', tipo: 'perdido', localizacao: null, data_registro: '2026-11-13T10:00:00Z' }
const MAIS_VELHO = { ...ITEM, id: 'item_1', data_registro: '2026-11-01T10:00:00Z' }

describe('lista do catálogo (SCRUM-97, US-04)', () => {
  it('Dado que existem itens publicados, quando acesso o catálogo sem entrar, vejo do mais recente para o mais antigo', async () => {
    simularApi({ itens: [MAIS_NOVO, MAIS_VELHO] })
    render(<App />)
    await screen.findByText('Carregador USB-C')
    const titulos = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)
    expect(titulos).toEqual(['Carregador USB-C', 'Garrafa térmica azul'])
  })

  it('a ordem é a da API: o site não reordena', async () => {
    // Mesmo que a API mandasse fora de ordem, a tela mostra o que veio. Ordenar é do servidor.
    simularApi({ itens: [MAIS_VELHO, MAIS_NOVO] })
    render(<App />)
    await screen.findByText('Carregador USB-C')
    const titulos = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)
    expect(titulos).toEqual(['Garrafa térmica azul', 'Carregador USB-C'])
  })

  it('cada item mostra tipo, descrição, local(is), data e situação', async () => {
    simularApi({ itens: [{ ...ITEM, local: ['Grad 5', 'Laboratório de hardware'] }] })
    render(<App />)
    const cartao = (await screen.findByText('Garrafa térmica azul')).closest('article')
    const dentro = within(cartao)
    expect(dentro.getByText('Achado')).toBeTruthy()
    expect(dentro.getByText('Grad 5, Laboratório de hardware')).toBeTruthy()
    expect(cartao.querySelector('time').getAttribute('dateTime')).toBe(ITEM.data_registro)
    expect(dentro.getByText(/aberto/)).toBeTruthy()
  })

  it('achados e perdidos aparecem juntos, numa lista só, sem abas', async () => {
    simularApi({ itens: [MAIS_NOVO, MAIS_VELHO] })
    render(<App />)
    await screen.findByText('Carregador USB-C')
    expect(screen.getAllByRole('list')).toHaveLength(1)
    expect(screen.queryByRole('tab')).toBeNull()
    expect(screen.getByText('Achado')).toBeTruthy()
    expect(screen.getByText('Perdido')).toBeTruthy()
  })

  it('a descrição leva à página do item', async () => {
    simularApi()
    render(<App />)
    const link = await screen.findByRole('link', { name: 'Garrafa térmica azul' })
    expect(link.getAttribute('href')).toBe('/itens/item_1')
  })

  it('os resultados avisam leitores de tela quando mudam', async () => {
    simularApi()
    render(<App />)
    await screen.findByText('Garrafa térmica azul')
    expect(screen.getByRole('region', { name: 'Resultados' }).getAttribute('aria-live')).toBe('polite')
  })
})

describe('paginação do catálogo (US-04)', () => {
  const tresPaginas = (url) => {
    const pagina = Number(new URL(url, 'http://x').searchParams.get('pagina') ?? 1)
    return respostaLista([{ ...ITEM, id: `item_p${pagina}`, descricao: `Item da página ${pagina}` }], {
      pagina_atual: pagina,
      total_paginas: 3,
      total_itens: 3,
      limite: 1,
    })
  }

  it('termo genérico com muitos resultados vem paginado, e "Mais antigos" vai à próxima página', async () => {
    irPara('/?tipo=achado')
    const api = simularApi({ itens: tresPaginas })
    render(<App />)
    await screen.findByText('Item da página 1')
    expect(screen.getByText('Página 1 de 3')).toBeTruthy()
    expect(screen.getByRole('button', { name: /Mais recentes/ }).disabled).toBe(true)

    fireEvent.click(screen.getByRole('button', { name: /Mais antigos/ }))
    await screen.findByText('Item da página 2')
    expect(chamadasDeItens(api).at(-1)).toBe('/api/itens?tipo=achado&pagina=2')
    expect(window.location.search).toBe('?tipo=achado&pagina=2')
  })

  it('a página da URL é respeitada ao abrir, e mudar um filtro volta à primeira', async () => {
    irPara('/?pagina=3')
    const api = simularApi({ itens: tresPaginas })
    render(<App />)
    await screen.findByText('Item da página 3')
    expect(screen.getByRole('button', { name: /Mais antigos/ }).disabled).toBe(true)

    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'perdido' } })
    await waitFor(() => expect(chamadasDeItens(api).at(-1)).toBe('/api/itens?tipo=perdido'))
    expect(window.location.search).toBe('?tipo=perdido')
  })

  it('com uma página só, não há paginação', async () => {
    simularApi()
    render(<App />)
    await screen.findByText('Garrafa térmica azul')
    expect(screen.queryByRole('navigation', { name: 'Páginas do catálogo' })).toBeNull()
  })
})
