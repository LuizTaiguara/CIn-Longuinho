// Um item na lista do catálogo (SCRUM-97, US-04): tipo, descrição, local(is), data e situação.
// A descrição é o link para a página do item.

import { Link } from 'react-router-dom'

const ROTULO_TIPO = { achado: 'Achado', perdido: 'Perdido' }

export default function CartaoItem({ item }) {
  return (
    <article className="item">
      <p className="etiquetas">
        <span className={`tipo tipo-${item.tipo}`}>{ROTULO_TIPO[item.tipo] ?? item.tipo}</span>
      </p>
      <h2 className="descricao">
        <Link to={`/itens/${encodeURIComponent(item.id)}`}>{item.descricao}</Link>
      </h2>
      <p className="detalhes">
        <span>{item.local.length ? item.local.join(', ') : 'Local não informado'}</span>
        {' · '}
        <time dateTime={item.data_registro}>{new Date(item.data_registro).toLocaleDateString('pt-BR')}</time>
      </p>
      <p className="situacao">{item.situacao}</p>
    </article>
  )
}
