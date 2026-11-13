// PROVISÓRIA. A lista de verdade (cartão do item, ordem, situação com tempo) é a SCRUM-97 e a
// SCRUM-99, do Pedro. Esta versão mínima existe só para a busca e os filtros (SCRUM-98) terem
// onde mostrar o resultado. Pode ser substituída por inteiro.

export default function ListaItens({ itens }) {
  return (
    <ul className="lista-itens">
      {itens.map((item) => (
        <li key={item.id} className="item">
          <span className={`tipo tipo-${item.tipo}`}>{item.tipo === 'achado' ? 'Achado' : 'Perdido'}</span>
          <p className="descricao">{item.descricao}</p>
          <p className="detalhes">
            {item.local?.length ? item.local.join(', ') : 'Local não informado'} · {item.situacao}
          </p>
        </li>
      ))}
    </ul>
  )
}
