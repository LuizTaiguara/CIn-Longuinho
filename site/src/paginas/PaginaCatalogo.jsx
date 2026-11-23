// Catálogo (US-04): busca, filtros, lista única e paginação. Aberto para leitura, sem login.

import { useRef } from 'react'
import BarraDeBusca from '../componentes/BarraDeBusca.jsx'
import EstadoDoCatalogo from '../componentes/EstadoDoCatalogo.jsx'
import ListaItens from '../componentes/ListaItens.jsx'
import Paginacao from '../componentes/Paginacao.jsx'
import { ESTADOS, estadoDoCatalogo } from '../estadoDoCatalogo.js'
import { FILTROS_VAZIOS } from '../filtros.js'
import { useItens, useLocais } from '../hooks/useCatalogo.js'
import { useFiltrosNaUrl } from '../hooks/useFiltrosNaUrl.js'

const contagem = (total) => (total === 1 ? '1 anúncio' : `${total} anúncios`)

export default function PaginaCatalogo() {
  const { filtros, pagina, mudarFiltros, mudarPagina } = useFiltrosNaUrl()
  const locais = useLocais()
  const itens = useItens(filtros, pagina)
  const estado = estadoDoCatalogo(itens, filtros)
  const resultados = useRef(null)

  // Ao trocar de página, o foco vai para o topo dos resultados (e a tela rola até lá).
  const trocarPagina = (nova) => {
    mudarPagina(nova)
    resultados.current?.focus()
  }

  return (
    <div className="catalogo">
      <h1 className="visualmente-oculto">Catálogo</h1>
      <div className="abertura">
        {/* Chamada pedida pelo PO em 23/11/2026. Não é um título: o h1 da página continua "Catálogo". */}
        <p className="chamada">
          O seu item em <em>3</em> cliquinhos
        </p>
        <p className="subtitulo">O que circula na lista achados-perdidos@cin.ufpe.br, num lugar só.</p>
      </div>
      <BarraDeBusca filtros={filtros} locais={locais} onMudar={mudarFiltros} />

      <section
        className="resultados"
        aria-label="Resultados"
        aria-live="polite"
        aria-busy={itens.carregando}
        tabIndex={-1}
        ref={resultados}
      >
        {estado === ESTADOS.COM_ITENS ? (
          <>
            <p className="contagem">{contagem(itens.resposta.paginacao?.total_itens ?? itens.resposta.itens.length)}</p>
            <ListaItens itens={itens.resposta.itens} />
            <Paginacao paginacao={itens.resposta.paginacao} onMudar={trocarPagina} />
          </>
        ) : (
          <EstadoDoCatalogo
            estado={estado}
            onLimparFiltros={() => mudarFiltros({ ...FILTROS_VAZIOS })}
            onTentarDeNovo={itens.tentarDeNovo}
          />
        )}
      </section>
    </div>
  )
}
