import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import App from '../App.jsx'
import { DETALHE, irPara, simularApi } from '../testes/apoio.js'
import { linkDeRemocao } from './Rodape.jsx'

beforeEach(() => irPara('/'))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('rodapé com o canal de remoção (SCRUM-58, US-09)', () => {
  it('Dado que apareço em um item sem tê-lo publicado, o rodapé indica o canal de contato', async () => {
    vi.stubEnv('VITE_EMAIL_REMOCAO', 'projeto+remocao@exemplo.invalid')
    simularApi()
    render(<App />)
    const rodape = screen.getByRole('contentinfo')
    expect(rodape.textContent).toMatch(/Apareceu num anúncio que não é seu e quer que ele saia do catálogo\? Escreva para/)
    const link = within(rodape).getByRole('link', { name: 'projeto+remocao@exemplo.invalid' })
    expect(link.getAttribute('href')).toMatch(/^mailto:projeto\+remocao@exemplo\.invalid\?/)
    await screen.findByText('Garrafa térmica azul')
  })

  it('sem VITE_EMAIL_REMOCAO, usa um endereço exemplo.invalid, nunca um endereço de pessoa', () => {
    vi.stubEnv('VITE_EMAIL_REMOCAO', '')
    simularApi()
    render(<App />)
    expect(within(screen.getByRole('contentinfo')).getByRole('link').textContent).toBe('remocao@exemplo.invalid')
  })

  it('aparece também na página do item, e o pedido já sai identificando o item', async () => {
    irPara('/itens/item_1')
    simularApi({ rotas: { 'GET /api/itens/item_1': () => [200, DETALHE] } })
    render(<App />)
    await screen.findByRole('heading', { level: 1 })
    const href = within(screen.getByRole('contentinfo')).getByRole('link').getAttribute('href')
    const corpo = decodeURIComponent(href.split('body=')[1])
    expect(decodeURIComponent(href)).toMatch(/subject=Pedido de remoção do anúncio item_1/)
    expect(corpo).toContain('/itens/item_1')
  })

  it('fora da página de um item, o pedido vai sem item', () => {
    expect(linkDeRemocao('r@exemplo.invalid', '/', 'http://site')).toBe(
      'mailto:r@exemplo.invalid?subject=Pedido%20de%20remo%C3%A7%C3%A3o%20de%20an%C3%BAncio',
    )
  })
})
