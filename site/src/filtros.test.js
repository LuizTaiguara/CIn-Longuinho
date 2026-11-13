import { describe, expect, it } from 'vitest'
import { FILTROS_VAZIOS, filtrosDaUrl, paramsDosFiltros, temFiltroAtivo } from './filtros.js'

describe('filtrosDaUrl', () => {
  it('lê os filtros da query', () => {
    expect(filtrosDaUrl('?texto=garrafa&local=Grad%205&tipo=achado&situacao=aberto')).toEqual({
      texto: 'garrafa',
      local: 'Grad 5',
      tipo: 'achado',
      situacao: 'aberto',
    })
  })

  it('sem query, não há filtro', () => {
    expect(filtrosDaUrl('')).toEqual(FILTROS_VAZIOS)
  })

  it('descarta tipo e situação fora do vocabulário fechado', () => {
    const filtros = filtrosDaUrl('?tipo=roubado&situacao=sumido')
    expect(filtros.tipo).toBe('')
    expect(filtros.situacao).toBe('')
  })

  it('não mexe em acento nem maiúscula: isso é do servidor', () => {
    expect(filtrosDaUrl('?texto=Óculos').texto).toBe('Óculos')
  })
})

describe('paramsDosFiltros', () => {
  it('só leva os filtros preenchidos', () => {
    const params = paramsDosFiltros({ ...FILTROS_VAZIOS, texto: '  chave ', tipo: 'perdido' })
    expect(params.toString()).toBe('texto=chave&tipo=perdido')
  })
})

describe('temFiltroAtivo', () => {
  it('é falso sem filtros e verdadeiro com qualquer um', () => {
    expect(temFiltroAtivo(FILTROS_VAZIOS)).toBe(false)
    expect(temFiltroAtivo({ ...FILTROS_VAZIOS, local: 'Grad 1' })).toBe(true)
  })
})
