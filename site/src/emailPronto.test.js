import { describe, expect, it } from 'vitest'
import { linkGmail, linkMailto, textoParaCopiar } from './emailPronto.js'

const EMAIL = {
  para: 'achados-perdidos@cin.ufpe.br',
  assunto: '[AP-K7F3Q2] Achado: garrafa & tampa',
  corpo: 'Achado: garrafa\nLink: http://site/itens/item_1?x=1',
}

describe('e-mail pronto (SCRUM-56, US-07)', () => {
  it('mailto com assunto e corpo codificados, e quebras de linha CRLF', () => {
    const link = linkMailto(EMAIL)
    expect(link.startsWith('mailto:achados-perdidos@cin.ufpe.br?subject=')).toBe(true)
    const params = new URLSearchParams(link.split('?').slice(1).join('?'))
    expect(params.get('subject')).toBe(EMAIL.assunto)
    expect(params.get('body')).toBe('Achado: garrafa\r\nLink: http://site/itens/item_1?x=1')
  })

  it('link do Gmail abre a tela de escrever com destinatário, assunto e corpo', () => {
    const url = new URL(linkGmail(EMAIL))
    expect(url.origin + url.pathname).toBe('https://mail.google.com/mail/')
    expect(url.searchParams.get('view')).toBe('cm')
    expect(url.searchParams.get('to')).toBe(EMAIL.para)
    expect(url.searchParams.get('su')).toBe(EMAIL.assunto)
    expect(url.searchParams.get('body')).toBe(EMAIL.corpo)
  })

  it('texto para copiar traz destinatário, assunto e corpo', () => {
    expect(textoParaCopiar(EMAIL)).toBe(`Para: ${EMAIL.para}\nAssunto: ${EMAIL.assunto}\n\n${EMAIL.corpo}`)
  })
})
