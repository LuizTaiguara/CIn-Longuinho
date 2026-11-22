import { describe, expect, it } from 'vitest'
import { textoDaLocalizacao, textoDaSituacao } from './situacao.js'

const AGORA = new Date('2026-11-15T12:00:00Z')

describe('textoDaSituacao (SCRUM-99, US-04)', () => {
  it('aberto é só "aberto"', () => {
    expect(textoDaSituacao({ situacao: 'aberto' }, AGORA)).toBe('aberto')
  })

  it('Dado um item reivindicado mas não confirmado, mostra a situação e há quanto tempo está nela', () => {
    const item = { situacao: 'reivindicado', data_situacao: '2026-10-25T12:00:00Z' }
    expect(textoDaSituacao(item, AGORA)).toBe('reivindicado há 3 semanas, retirada não confirmada')
  })

  it('reivindicado há pouco também mostra o tempo: "há 2 horas" não é "há 3 semanas"', () => {
    const item = { situacao: 'reivindicado', data_situacao: '2026-11-15T10:00:00Z' }
    expect(textoDaSituacao(item, AGORA)).toBe('reivindicado há 2 horas, retirada não confirmada')
  })

  it('reivindicado ontem', () => {
    const item = { situacao: 'reivindicado', data_situacao: '2026-11-14T09:00:00Z' }
    expect(textoDaSituacao(item, AGORA)).toBe('reivindicado ontem, retirada não confirmada')
  })

  it('encerrado pelo autor é "encerrado"', () => {
    expect(textoDaSituacao({ situacao: 'encerrado', fonte_encerramento: 'confirmação do autor' }, AGORA)).toBe('encerrado')
  })
})

describe('textoDaSituacao com a fonte do encerramento (SCRUM-53, US-04, US-10)', () => {
  it('encerrado por terceiro é "encerrado segundo terceiro", e não só "encerrado"', () => {
    expect(textoDaSituacao({ situacao: 'encerrado', fonte_encerramento: 'terceiro' }, AGORA)).toBe('encerrado segundo terceiro')
  })
})

describe('textoDaLocalizacao (SCRUM-53)', () => {
  it('setor aparece com o nome', () => {
    expect(textoDaLocalizacao({ tipo: 'achado', localizacao: 'com um setor', setor: 'SecGrad' })).toBe('está com um setor: SecGrad')
  })

  it('setor sem nome não inventa nome', () => {
    expect(textoDaLocalizacao({ tipo: 'achado', localizacao: 'com um setor', setor: null })).toBe('está com um setor')
  })

  it('perdido não tem localização, mesmo que viesse preenchida', () => {
    expect(textoDaLocalizacao({ tipo: 'perdido', localizacao: 'no local' })).toBeNull()
  })

  it('achado sem localização não mostra nada', () => {
    expect(textoDaLocalizacao({ tipo: 'achado', localizacao: null })).toBeNull()
  })
})
