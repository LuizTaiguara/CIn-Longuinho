// Lista única do catálogo (SCRUM-97, US-04): achados e perdidos juntos, na ordem em que a API
// devolve (mais recente primeiro). O site não reordena nem filtra nada por conta própria.

import CartaoItem from './CartaoItem.jsx'

export default function ListaItens({ itens }) {
  return (
    <ul className="lista-itens">
      {itens.map((item) => (
        <li key={item.id}>
          <CartaoItem item={item} />
        </li>
      ))}
    </ul>
  )
}
