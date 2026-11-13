import BarraDeBusca from './componentes/BarraDeBusca.jsx'
import ListaItens from './componentes/ListaItens.jsx'
import { useItens, useLocais } from './hooks/useCatalogo.js'
import { useFiltrosNaUrl } from './hooks/useFiltrosNaUrl.js'

export default function App() {
  const [filtros, mudarFiltros] = useFiltrosNaUrl()
  const locais = useLocais()
  const itens = useItens(filtros)

  return (
    <div className="pagina">
      <header className="cabecalho">
        <h1>Achados e Perdidos do CIn</h1>
        <p>O que circula na lista achados-perdidos@cin.ufpe.br, num lugar só.</p>
      </header>

      <BarraDeBusca filtros={filtros} locais={locais} onMudar={mudarFiltros} />

      <main aria-live="polite" aria-busy={itens.carregando}>
        {itens.carregando && !itens.resposta && <p className="aviso">Carregando o catálogo…</p>}
        {itens.erro && <p className="aviso">Não foi possível carregar o catálogo.</p>}
        {itens.resposta && <ListaItens itens={itens.resposta.itens} />}
      </main>
    </div>
  )
}
