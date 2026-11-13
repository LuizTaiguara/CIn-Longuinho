// Mensagens dos estados sem lista (SCRUM-100, US-04).
// Os textos são provisórios até os wireframes da Klarissa (F-04). Mudar o sentido deles é decisão do PO.

import { ESTADOS } from '../estadoDoCatalogo.js'

export default function EstadoDoCatalogo({ estado, onLimparFiltros, onTentarDeNovo }) {
  if (estado === ESTADOS.CARREGANDO) {
    return <p className="aviso">Carregando o catálogo…</p>
  }

  if (estado === ESTADOS.VAZIO) {
    return (
      <section className="estado">
        <h2>Ainda não há itens no catálogo</h2>
        <p>
          Os anúncios chegam pela lista <strong>achados-perdidos@cin.ufpe.br</strong> e aparecem aqui
          depois de processados. Isso não é um defeito: o catálogo só está começando.
        </p>
      </section>
    )
  }

  if (estado === ESTADOS.SEM_RESULTADO) {
    return (
      <section className="estado">
        <h2>Nada encontrado para essa busca</h2>
        <p>Tente buscar com menos termos ou tirar algum filtro.</p>
        <p>
          Se o anúncio acabou de ser enviado para a lista, ele pode ainda não ter sido processado.
          Vale procurar de novo mais tarde.
        </p>
        <button type="button" onClick={onLimparFiltros}>
          Ver o catálogo inteiro
        </button>
      </section>
    )
  }

  if (estado === ESTADOS.ERRO) {
    return (
      <section className="estado estado-erro" role="alert">
        <h2>O catálogo está fora do ar agora</h2>
        <p>
          Não conseguimos fazer a busca. <strong>Isso não quer dizer que nada foi encontrado</strong>: o
          catálogo está temporariamente indisponível. Tente de novo em alguns minutos.
        </p>
        <button type="button" onClick={onTentarDeNovo}>
          Tentar de novo
        </button>
      </section>
    )
  }

  return null
}
