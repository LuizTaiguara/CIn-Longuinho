// Qual tela o catálogo mostra (SCRUM-100). Nenhum estado é tela em branco.
//
// A distinção que importa: "nada encontrado" e "não consegui procurar" são coisas diferentes.
// Se a API falhou, o catálogo NUNCA mostra lista vazia, porque isso faria a pessoa concluir
// que ninguém achou o objeto dela.

import { temFiltroAtivo } from './filtros.js'

export const ESTADOS = Object.freeze({
  CARREGANDO: 'carregando',
  ERRO: 'erro',
  VAZIO: 'vazio', // catálogo sem nenhum item (ex.: primeira execução)
  SEM_RESULTADO: 'sem-resultado', // há itens, mas nenhum corresponde à busca
  COM_ITENS: 'com-itens',
})

export function estadoDoCatalogo({ carregando, erro, resposta }, filtros) {
  if (erro) return ESTADOS.ERRO
  if (carregando || !resposta) return ESTADOS.CARREGANDO
  if (resposta.itens.length > 0) return ESTADOS.COM_ITENS
  return temFiltroAtivo(filtros) ? ESTADOS.SEM_RESULTADO : ESTADOS.VAZIO
}
