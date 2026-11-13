import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from '../App.jsx'
import { ITEM, chamadasDeItens, simularApi } from '../testes/apoio.js'

beforeEach(() => window.history.replaceState(null, '', '/'))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('estados vazios e de erro (SCRUM-100)', () => {
  it('catálogo vazio explica que os anúncios chegam pela lista', async () => {
    simularApi({ itens: [] })
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Ainda não há itens no catálogo' })).toBeTruthy()
    expect(screen.getByText(/achados-perdidos@cin\.ufpe\.br/, { selector: 'strong' })).toBeTruthy()
  })

  it('busca sem resultado sugere menos termos e lembra do processamento', async () => {
    window.history.replaceState(null, '', '/?texto=guarda-chuva')
    simularApi({ itens: [] })
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Nada encontrado para essa busca' })).toBeTruthy()
    expect(screen.getByText(/menos termos/)).toBeTruthy()
    expect(screen.getByText(/ainda não ter sido processado/)).toBeTruthy()
  })

  it('"Ver o catálogo inteiro" tira os filtros', async () => {
    window.history.replaceState(null, '', '/?texto=guarda-chuva')
    const api = simularApi({ itens: (url) => (url.includes('texto=') ? [] : [ITEM]) })
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Ver o catálogo inteiro' }))
    await screen.findByText('Garrafa térmica azul')
    expect(chamadasDeItens(api).at(-1)).toBe('/api/itens')
  })

  it('banco fora mostra erro honesto, sem lista e sem detalhe técnico', async () => {
    simularApi({ itens: 503 })
    render(<App />)
    const alerta = await screen.findByRole('alert')
    expect(alerta.textContent).toMatch(/não quer dizer que nada foi encontrado/)
    expect(alerta.textContent).not.toMatch(/503|INDISPONIVEL|Error/)
    expect(screen.queryByRole('heading', { name: /Nada encontrado|Ainda não há itens/ })).toBeNull()
  })

  it('falha de rede também é erro, não catálogo vazio', async () => {
    simularApi({ itens: 'rede' })
    render(<App />)
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.queryByText('Ainda não há itens no catálogo')).toBeNull()
  })

  it('"Tentar de novo" refaz a busca e mostra a lista quando a API volta', async () => {
    let fora = true
    const api = simularApi({ itens: () => [ITEM] })
    const fetchOriginal = api.getMockImplementation()
    api.mockImplementation((url) => {
      if (fora && String(url).startsWith('/api/itens')) {
        return Promise.resolve(new Response('{}', { status: 503 }))
      }
      return fetchOriginal(url)
    })
    render(<App />)
    await screen.findByRole('alert')
    fora = false
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    await screen.findByText('Garrafa térmica azul')
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull())
  })
})
