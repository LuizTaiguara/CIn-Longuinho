import BarraDeBusca from './componentes/BarraDeBusca.jsx'
import EstadoDoCatalogo from './componentes/EstadoDoCatalogo.jsx'
import ListaItens from './componentes/ListaItens.jsx'
import { ESTADOS, estadoDoCatalogo } from './estadoDoCatalogo.js'
import { FILTROS_VAZIOS } from './filtros.js'
import { useItens, useLocais } from './hooks/useCatalogo.js'
import { useFiltrosNaUrl } from './hooks/useFiltrosNaUrl.js'

export default function App() {
  const [filtros, mudarFiltros] = useFiltrosNaUrl()
  const locais = useLocais()
  const itens = useItens(filtros)
  const estado = estadoDoCatalogo(itens, filtros)

  return (
    <div className="pagina">
      <header className="cabecalho">
        <h1>Achados e Perdidos do CIn</h1>
        <p>O que circula na lista achados-perdidos@cin.ufpe.br, num lugar só.</p>
      </header>

      <BarraDeBusca filtros={filtros} locais={locais} onMudar={mudarFiltros} />

      <main aria-live="polite" aria-busy={itens.carregando}>
        {estado === ESTADOS.COM_ITENS ? (
          <ListaItens itens={itens.resposta.itens} />
        ) : (
          <EstadoDoCatalogo
            estado={estado}
            onLimparFiltros={() => mudarFiltros({ ...FILTROS_VAZIOS })}
            onTentarDeNovo={itens.tentarDeNovo}
          />
        )}
      </main>
    </div>
  )
}
