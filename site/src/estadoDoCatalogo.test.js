import { describe, expect, it } from 'vitest'
import { ESTADOS, estadoDoCatalogo } from './estadoDoCatalogo.js'
import { FILTROS_VAZIOS } from './filtros.js'
import { ITEM, respostaLista } from './testes/apoio.js'

const comFiltro = { ...FILTROS_VAZIOS, texto: 'guarda-chuva' }

describe('estadoDoCatalogo', () => {
  it('falha da API é erro, nunca lista vazia', () => {
    const erro = new Error('fora')
    expect(estadoDoCatalogo({ carregando: false, erro, resposta: null }, FILTROS_VAZIOS)).toBe(ESTADOS.ERRO)
    expect(estadoDoCatalogo({ carregando: false, erro, resposta: null }, comFiltro)).toBe(ESTADOS.ERRO)
  })

  it('zero itens sem filtro é catálogo vazio', () => {
    const resposta = respostaLista([])
    expect(estadoDoCatalogo({ carregando: false, erro: null, resposta }, FILTROS_VAZIOS)).toBe(ESTADOS.VAZIO)
  })

  it('zero itens com filtro é busca sem resultado', () => {
    const resposta = respostaLista([])
    expect(estadoDoCatalogo({ carregando: false, erro: null, resposta }, comFiltro)).toBe(ESTADOS.SEM_RESULTADO)
  })

  it('com itens, mostra a lista', () => {
    const resposta = respostaLista([ITEM])
    expect(estadoDoCatalogo({ carregando: false, erro: null, resposta }, comFiltro)).toBe(ESTADOS.COM_ITENS)
  })

  it('antes da primeira resposta, está carregando', () => {
    expect(estadoDoCatalogo({ carregando: true, erro: null, resposta: null }, FILTROS_VAZIOS)).toBe(ESTADOS.CARREGANDO)
  })
})
