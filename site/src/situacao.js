// Como a situação e a localização aparecem na tela (SCRUM-99, SCRUM-53, US-04). A tela LÊ o que
// vem da API: não calcula, não infere e não esconde item nenhum. O texto é "com honestidade"
// (site/AGENTS.md).

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
      // Encerrado por declaração de outra pessoa na thread (US-10): diz de onde veio a informação.
      return item.fonte_encerramento === 'terceiro' ? 'encerrado segundo terceiro' : 'encerrado'
    default:
      return item.situacao ?? ''
  }
}

const TEXTO_DA_LOCALIZACAO = {
  'no local': 'está no local',
  'com quem achou': 'está com quem achou',
  'com um setor': 'está com um setor',
  'caixa do bloco A/E': 'na caixa do bloco A/E',
  devolvido: 'devolvido',
}

// Onde o objeto está agora, como foi declarado. Perdido não tem localização: quem perdeu não sabe.
export function textoDaLocalizacao(item) {
  if (item.tipo !== 'achado' || !item.localizacao) return null
  if (item.localizacao === 'com um setor' && item.setor) return `está com um setor: ${item.setor}`
  return TEXTO_DA_LOCALIZACAO[item.localizacao] ?? item.localizacao
}
