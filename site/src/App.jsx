// Casca do site: cabeçalho, rotas e rodapé em todas as telas.
// O roteador fica aqui dentro para que a URL do navegador seja a fonte de verdade
// (filtros, página, item aberto) e os testes possam renderizar <App /> direto.

import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Rodape from './componentes/Rodape.jsx'
import { ProvedorSessao } from './hooks/useSessao.js'
import PaginaCatalogo from './paginas/PaginaCatalogo.jsx'
import PaginaItem from './paginas/PaginaItem.jsx'

function NaoEncontrada() {
  return (
    <section className="estado">
      <h2>Esta página não existe</h2>
      <p>
        <Link to="/">Voltar ao catálogo</Link>
      </p>
    </section>
  )
}

function Casca() {
  return (
    <div className="pagina">
      <header className="cabecalho">
        <p className="titulo">
          <Link to="/">Achados e Perdidos do CIn</Link>
        </p>
        <p className="subtitulo">O que circula na lista achados-perdidos@cin.ufpe.br, num lugar só.</p>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<PaginaCatalogo />} />
          <Route path="/itens/:id" element={<PaginaItem />} />
          <Route path="*" element={<NaoEncontrada />} />
        </Routes>
      </main>

      <Rodape />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ProvedorSessao>
        <Casca />
      </ProvedorSessao>
    </BrowserRouter>
  )
}
