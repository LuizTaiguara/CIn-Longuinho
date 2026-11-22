// Casca do site: cabeçalho, rotas e rodapé em todas as telas.
// O roteador fica aqui dentro para que a URL do navegador seja a fonte de verdade
// (filtros, página, item aberto) e os testes possam renderizar <App /> direto.

import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Cabecalho from './componentes/Cabecalho.jsx'
import ExigeSessao from './componentes/ExigeSessao.jsx'
import Rodape from './componentes/Rodape.jsx'
import { ProvedorSessao } from './hooks/useSessao.js'
import PaginaCadastrar from './paginas/PaginaCadastrar.jsx'
import PaginaCatalogo from './paginas/PaginaCatalogo.jsx'
import PaginaItem from './paginas/PaginaItem.jsx'
import PaginaLogin from './paginas/PaginaLogin.jsx'
import PaginaMeusAnuncios from './paginas/PaginaMeusAnuncios.jsx'

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
      {/* Primeiro foco do teclado: pula o cabeçalho e vai direto ao conteúdo. */}
      <a className="pular" href="#conteudo">
        Ir para o conteúdo
      </a>
      <Cabecalho />

      <main id="conteudo" tabIndex={-1}>
        <Routes>
          <Route path="/" element={<PaginaCatalogo />} />
          <Route path="/itens/:id" element={<PaginaItem />} />
          <Route path="/login" element={<PaginaLogin />} />
          <Route
            path="/cadastrar"
            element={
              <ExigeSessao>
                <PaginaCadastrar />
              </ExigeSessao>
            }
          />
          <Route
            path="/meus-anuncios"
            element={
              <ExigeSessao>
                <PaginaMeusAnuncios />
              </ExigeSessao>
            }
          />
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
