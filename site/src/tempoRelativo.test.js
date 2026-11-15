import { describe, expect, it } from 'vitest'
import { dataCompleta, tempoRelativo } from './tempoRelativo.js'

const AGORA = new Date('2026-11-15T12:00:00Z')
const antes = (ms) => new Date(AGORA.getTime() - ms).toISOString()
const MIN = 60 * 1000
const HORA = 60 * MIN
const DIA = 24 * HORA

describe('tempoRelativo', () => {
  it.each([
    [0, 'agora há pouco'],
    [30 * 1000, 'agora há pouco'],
    [1 * MIN, 'há 1 minuto'],
    [45 * MIN, 'há 45 minutos'],
    [1 * HORA, 'há 1 hora'],
    [2 * HORA, 'há 2 horas'],
    [23 * HORA, 'há 23 horas'],
    [1 * DIA, 'ontem'],
    [47 * HORA, 'ontem'],
    [2 * DIA, 'há 2 dias'],
    [3 * DIA, 'há 3 dias'],
    [7 * DIA, 'há 1 semana'],
    [21 * DIA, 'há 3 semanas'],
    [29 * DIA, 'há 4 semanas'],
    [30 * DIA, 'há 1 mês'],
    [95 * DIA, 'há 3 meses'],
    [365 * DIA, 'há 1 ano'],
    [800 * DIA, 'há 2 anos'],
  ])('%i ms atrás é "%s"', (ms, esperado) => {
    expect(tempoRelativo(antes(ms), AGORA)).toBe(esperado)
  })

  it('data no futuro (relógio adiantado) vira "agora há pouco"', () => {
    expect(tempoRelativo('2026-11-15T12:05:00Z', AGORA)).toBe('agora há pouco')
  })

  it('data inválida não quebra a tela', () => {
    expect(tempoRelativo('não é data', AGORA)).toBe('')
    expect(dataCompleta(null)).toBe('')
    expect(tempoRelativo(undefined, AGORA)).toBe('')
  })
})

describe('dataCompleta', () => {
  it('mostra dia, mês por extenso, ano e hora no fuso do Recife', () => {
    // 14:32 UTC = 11:32 no Recife (UTC-3, sem horário de verão).
    expect(dataCompleta('2026-11-12T14:32:00Z')).toBe('12 de novembro de 2026 às 11:32')
  })
})
