// Um item na lista do catálogo (SCRUM-97, US-04): tipo, descrição, local(is), data e situação.
// A descrição é o link para a página do item.
//
// Desenho (SCRUM-47): cada anúncio é um "crachá". A faixa do topo diz o tipo, o nome do objeto vem
// grande e a situação fica sempre na última linha, com um desenho próprio além do texto.

import { Link, useLocation } from 'react-router-dom'
import { textoDaLocalizacao, textoDaSituacao } from '../situacao.js'
import { dataCompleta, tempoRelativo } from '../tempoRelativo.js'
import Icone from './Icone.jsx'
import SeloRevisar from './SeloRevisar.jsx'

export const ROTULO_TIPO = { achado: 'Achado', perdido: 'Perdido' }

// A faixa do tipo, igual na lista, na página do item e em "Meus anúncios".
export function FaixaDoTipo({ item, children }) {
  return (
    <p className="faixa">
      <span className="tipo">
        <Icone nome={item.tipo} tamanho={16} />
        <span>{ROTULO_TIPO[item.tipo] ?? item.tipo}</span>
      </span>
      {item.revisar && <SeloRevisar />}
      {children}
    </p>
  )
}

export function classesDoCracha(item) {
  return `cracha cracha-${item.tipo}${item.situacao === 'encerrado' ? ' cracha-encerrado' : ''}`
}

export default function CartaoItem({ item }) {
  const { search } = useLocation()
  const localizacao = textoDaLocalizacao(item)

  return (
    <article className={classesDoCracha(item)}>
      <FaixaDoTipo item={item}>
        <time className="quando" dateTime={item.data_registro} title={dataCompleta(item.data_registro)}>
          {tempoRelativo(item.data_registro)}
        </time>
      </FaixaDoTipo>
      <div className="cracha-corpo">
        <h2 className="nome">
          {/* Guarda a busca atual para o "Voltar ao catálogo" da página do item não perder os filtros. */}
          <Link to={`/itens/${encodeURIComponent(item.id)}`} state={{ voltar: search }}>
            {item.descricao}
          </Link>
        </h2>
        <p className="onde">
          <Icone nome="local" tamanho={16} />
          <span>{item.local.length ? item.local.join(', ') : 'Local não informado'}</span>
        </p>
        <p className={`situacao situacao-${item.situacao}`}>
          <Icone nome={item.situacao} tamanho={16} />
          <span>
            <span className="visualmente-oculto">Situação: </span>
            <span title={item.data_situacao ? `Desde ${dataCompleta(item.data_situacao)}` : undefined}>
              {textoDaSituacao(item)}
            </span>
            {localizacao && <span className="localizacao"> · {localizacao}</span>}
          </span>
        </p>
      </div>
    </article>
  )
}
