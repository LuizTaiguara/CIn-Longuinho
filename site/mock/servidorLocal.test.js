import { describe, expect, it } from 'vitest'
import { itens } from './dados.js'
import { filtrarItens, paginar } from './servidorLocal.js'

const q = (texto) => new URLSearchParams(texto)

describe('mock local de GET /api/itens', () => {
  it('busca sem acento e sem maiúscula', () => {
    expect(filtrarItens(itens, q('texto=OCULOS')).map((i) => i.id)).toEqual(['item_0009'])
  })

  it('filtro de local inclui item que cita vários locais', () => {
    const ids = filtrarItens(itens, q('local=Grad 4')).map((i) => i.id)
    expect(ids).toContain('item_0005')
    expect(ids).toContain('item_0006')
  })

  it('ordena do mais recente para o mais antigo', () => {
    const datas = filtrarItens(itens, q('')).map((i) => i.data_registro)
    expect(datas).toEqual([...datas].sort().reverse())
  })

  it('pagina com os metadados do contrato', () => {
    const { paginacao } = paginar(itens, q('limite=3&pagina=2'))
    expect(paginacao).toEqual({ pagina_atual: 2, total_paginas: 3, total_itens: itens.length, limite: 3 })
  })
})
