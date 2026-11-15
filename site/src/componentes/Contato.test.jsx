import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from '../App.jsx'
import { lerRascunho } from '../rascunho.js'
import { DETALHE, chamadasA, irPara, simularApi } from '../testes/apoio.js'

beforeEach(() => irPara('/itens/item_1'))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

const NOME = 'Pessoa Fictícia'
const MENSAGEM = 'Acho que essa garrafa é minha, tem um adesivo na tampa.'

const comContato = (resposta, { sessao = NOME, item = DETALHE } = {}) =>
  simularApi({
    sessao,
    rotas: {
      'GET /api/itens/item_1': () => [200, item],
      'POST /api/itens/item_1/contato': resposta,
    },
  })

async function escreverEEnviar(texto = MENSAGEM) {
  fireEvent.change(await screen.findByLabelText('Sua mensagem'), { target: { value: texto } })
  fireEvent.click(screen.getByRole('button', { name: 'Enviar mensagem' }))
}

describe('botão de contato (SCRUM-103, US-05)', () => {
  it('Dado que quero falar com quem anunciou, minha mensagem vai pela API sem que eu veja o endereço', async () => {
    const api = comContato(() => [202, null])
    render(<App />)
    const secao = await screen.findByRole('region', { name: 'Falar com quem anunciou' })
    expect(within(secao).getByText(/Você não vê o endereço dela/)).toBeTruthy()
    await escreverEEnviar()
    expect(await screen.findByText('Mensagem enviada.')).toBeTruthy()
    const [chamada] = chamadasA(api, 'POST', '/api/itens/item_1/contato')
    // Só a mensagem: nenhum campo de e-mail sai do site.
    expect(chamada.corpo).toEqual({ mensagem: MENSAGEM })
  })

  it('a tela não tem campo de e-mail nem mostra endereço nenhum', async () => {
    comContato(() => [202, null])
    render(<App />)
    await screen.findByLabelText('Sua mensagem')
    expect(document.querySelector('input[type="email"]')).toBeNull()
    expect(screen.queryByLabelText(/e-mail/i)).toBeNull()
    // No conteúdo da página (fora o rodapé, que tem o endereço público de remoção), nenhum e-mail.
    expect(document.querySelector('main').textContent).not.toMatch(/[\w.+-]+@[\w-]+\.[\w.]+/)
  })

  it('Envio de contato falha (502): explica e sugere tentar mais tarde, sem perder o texto', async () => {
    comContato(() => [502, { codigo: 'ENVIO_FALHOU' }])
    render(<App />)
    await escreverEEnviar()
    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível enviar. Tente mais tarde.')
    expect(screen.getByLabelText('Sua mensagem').value).toBe(MENSAGEM)
    expect(screen.queryByText('Mensagem enviada.')).toBeNull()
  })

  it('falha de rede também avisa, para ninguém esperar resposta de mensagem que não saiu', async () => {
    comContato(() => 'rede')
    render(<App />)
    await escreverEEnviar()
    expect((await screen.findByRole('alert')).textContent).toBe('Não foi possível enviar. Tente mais tarde.')
  })

  it('mensagem com menos de 10 caracteres mostra o erro no campo e não envia', async () => {
    const api = comContato(() => [202, null])
    render(<App />)
    await escreverEEnviar('oi')
    expect(await screen.findByText('Escreva pelo menos 10 caracteres.')).toBeTruthy()
    expect(chamadasA(api, 'POST', '/api/itens/item_1/contato')).toHaveLength(0)
  })

  it('o campo para em 2000 caracteres e mostra a contagem', async () => {
    comContato(() => [202, null])
    render(<App />)
    const campo = await screen.findByLabelText('Sua mensagem')
    expect(campo.getAttribute('maxLength')).toBe('2000')
    fireEvent.change(campo, { target: { value: 'abc' } })
    expect(screen.getByText('3 de 2000 caracteres')).toBeTruthy()
  })

  it('clique duplo envia uma vez só', async () => {
    let liberar
    const api = comContato(() => [202, null])
    const original = api.getMockImplementation()
    api.mockImplementation((url, init) =>
      String(url).endsWith('/contato') ? new Promise((r) => (liberar = () => r(original(url, init)))) : original(url, init),
    )
    render(<App />)
    await escreverEEnviar()
    fireEvent.click(screen.getByRole('button', { name: 'Enviando…' }))
    liberar()
    expect(await screen.findByText('Mensagem enviada.')).toBeTruthy()
    expect(chamadasA(api, 'POST', '/api/itens/item_1/contato')).toHaveLength(1)
  })

  it('sem sessão, convida a entrar com a conta do CIn, voltando ao item', async () => {
    comContato(() => [202, null], { sessao: null })
    render(<App />)
    const link = await screen.findByRole('link', { name: 'Entre com a conta do CIn para falar com quem anunciou' })
    expect(link.getAttribute('href')).toBe('/api/auth/google?retorno=%2Fitens%2Fitem_1')
    expect(screen.queryByLabelText('Sua mensagem')).toBeNull()
  })

  it('no meu próprio anúncio não aparece o contato', async () => {
    comContato(() => [202, null], { item: { ...DETALHE, pode_gerir: true } })
    render(<App />)
    await screen.findByRole('button', { name: 'Corrigir' })
    expect(screen.queryByRole('region', { name: 'Falar com quem anunciou' })).toBeNull()
  })

  it('sessão expirada no envio guarda a mensagem e manda ao login; ao voltar, a mensagem está lá', async () => {
    comContato(() => [401, { codigo: 'NAO_AUTENTICADO' }])
    render(<App />)
    await escreverEEnviar()
    await waitFor(() => expect(window.location.pathname).toBe('/login'))
    expect(lerRascunho('contato:item_1')).toEqual({ mensagem: MENSAGEM })

    cleanup()
    irPara('/itens/item_1')
    comContato(() => [202, null])
    render(<App />)
    expect((await screen.findByLabelText('Sua mensagem')).value).toBe(MENSAGEM)
  })
})
