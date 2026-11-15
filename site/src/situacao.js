// Como a situação aparece na tela (SCRUM-99, US-04). A tela LÊ a situação que vem da API: não
// calcula, não infere e não esconde item nenhum. O texto é "com honestidade" (site/AGENTS.md).

import { tempoRelativo } from './tempoRelativo.js'

export function textoDaSituacao(item, agora = new Date()) {
  switch (item.situacao) {
    case 'aberto':
      return 'aberto'
    case 'reivindicado': {
      // Quem procura decide se vale passar no local: o sistema informa há quanto tempo, não arbitra.
      const tempo = item.data_situacao ? tempoRelativo(item.data_situacao, agora) : ''
      return `reivindicado${tempo ? ` ${tempo}` : ''}, retirada não confirmada`
    }
    case 'encerrado':
      return 'encerrado'
    default:
      return item.situacao ?? ''
  }
}
