// Um item na lista do catálogo (SCRUM-97, US-04): tipo, descrição, local(is), data e situação.
// A descrição é o link para a página do item.

import { Link, useLocation } from 'react-router-dom'
import { textoDaLocalizacao, textoDaSituacao } from '../situacao.js'
import { dataCompleta, tempoRelativo } from '../tempoRelativo.js'
import SeloRevisar from './SeloRevisar.jsx'

export const ROTULO_TIPO = { achado: 'Achado', perdido: 'Perdido' }

export default function CartaoItem({ item }) {
  const { search } = useLocation()
  const localizacao = textoDaLocalizacao(item)

  return (
    <article className="item">
      <p className="etiquetas">
        <span className={`tipo tipo-${item.tipo}`}>{ROTULO_TIPO[item.tipo] ?? item.tipo}</span>
        {item.revisar && <SeloRevisar />}
      </p>
      <h2 className="descricao">
        {/* Guarda a busca atual para o "Voltar ao catálogo" da página do item não perder os filtros. */}
        <Link to={`/itens/${encodeURIComponent(item.id)}`} state={{ voltar: search }}>
          {item.descricao}
        </Link>
      </h2>
      <p className="detalhes">
        <span>{item.local.length ? item.local.join(', ') : 'Local não informado'}</span>
        {' · '}
        <time dateTime={item.data_registro} title={dataCompleta(item.data_registro)}>
          {tempoRelativo(item.data_registro)}
        </time>
      </p>
      <p className={`situacao situacao-${item.situacao}`}>
        <span className="visualmente-oculto">Situação: </span>
        <span title={item.data_situacao ? `Desde ${dataCompleta(item.data_situacao)}` : undefined}>
          {textoDaSituacao(item)}
        </span>
        {localizacao && <span className="localizacao"> · {localizacao}</span>}
      </p>
    </article>
  )
}
