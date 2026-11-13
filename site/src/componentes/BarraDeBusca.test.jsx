import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from '../App.jsx'
import { chamadasDeItens, simularApi } from '../testes/apoio.js'

beforeEach(() => window.history.replaceState(null, '', '/'))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('busca e filtros do catálogo (SCRUM-98)', () => {
  it('abre com achados e perdidos juntos, sem filtro na chamada', async () => {
    const api = simularApi()
    render(<App />)
    await screen.findByText('Garrafa térmica azul')
    expect(chamadasDeItens(api)).toEqual(['/api/itens'])
    expect(screen.getByLabelText('Tipo').value).toBe('')
  })

  it('o dropdown de local usa a lista de locais da API', async () => {
    simularApi()
    render(<App />)
    const select = screen.getByLabelText('Local')
    await waitFor(() => expect(select.disabled).toBe(false))
    const opcoes = [...select.options].map((opcao) => opcao.textContent)
    expect(opcoes).toEqual(['Todos os locais', 'Grad 1', 'Grad 5', 'Anfiteatro'])
  })

  it('filtrar por local manda o filtro à API e põe na URL', async () => {
    const api = simularApi()
    render(<App />)
    const select = screen.getByLabelText('Local')
    await waitFor(() => expect(select.disabled).toBe(false))
    fireEvent.change(select, { target: { value: 'Grad 5' } })
    await waitFor(() => expect(chamadasDeItens(api)).toContain('/api/itens?local=Grad+5'))
    expect(window.location.search).toBe('?local=Grad+5')
  })

  it('a busca por termo só vai à API ao enviar, sem normalizar no cliente', async () => {
    const api = simularApi()
    render(<App />)
    await screen.findByText('Garrafa térmica azul')
    fireEvent.change(screen.getByLabelText('O que você procura?'), { target: { value: 'Óculos' } })
    expect(chamadasDeItens(api)).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Buscar' }))
    await waitFor(() => expect(chamadasDeItens(api)).toContain('/api/itens?texto=%C3%93culos'))
  })

  it('filtra só achados ou só perdidos', async () => {
    const api = simularApi()
    render(<App />)
    await screen.findByText('Garrafa térmica azul')
    fireEvent.change(screen.getByLabelText('Tipo'), { target: { value: 'perdido' } })
    await waitFor(() => expect(chamadasDeItens(api)).toContain('/api/itens?tipo=perdido'))
  })

  it('lê os filtros de uma URL compartilhada', async () => {
    window.history.replaceState(null, '', '/?texto=chave&situacao=aberto')
    const api = simularApi()
    render(<App />)
    await waitFor(() => expect(chamadasDeItens(api)).toEqual(['/api/itens?texto=chave&situacao=aberto']))
    expect(screen.getByLabelText('O que você procura?').value).toBe('chave')
  })

  it('"Limpar filtros" volta ao catálogo inteiro', async () => {
    window.history.replaceState(null, '', '/?tipo=achado')
    const api = simularApi()
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Limpar filtros' }))
    await waitFor(() => expect(chamadasDeItens(api).at(-1)).toBe('/api/itens'))
    expect(window.location.search).toBe('')
  })

  it('sem a lista de locais, o catálogo continua funcionando', async () => {
    simularApi({ locais: 503 })
    render(<App />)
    await screen.findByText('Garrafa térmica azul')
    await waitFor(() => expect(screen.getByLabelText('Local').disabled).toBe(true))
    expect(screen.getByRole('option', { name: 'Locais indisponíveis' })).toBeTruthy()
  })
})
