// Cabeçalho de todas as telas: título e, à direita, "Entrar com a conta do CIn" ou
// "Meus anúncios" + "Sair". O botão de entrar é um link para a API, que fala com o Google.

import { Link, useLocation, useNavigate } from 'react-router-dom'
import { linkDeLogin } from '../api/cliente.js'
import { useSessao } from '../hooks/useSessao.js'
import { retornoSeguro } from '../rotasDoLogin.js'

export default function Cabecalho() {
  const sessao = useSessao()
  const location = useLocation()
  const navigate = useNavigate()

  // Na tela de login, o retorno é o que ela recebeu; nas outras, a própria página.
  const retorno =
    location.pathname === '/login'
      ? retornoSeguro(new URLSearchParams(location.search).get('retorno'))
      : `${location.pathname}${location.search}`

  const sair = async () => {
    try {
      await sessao.sair()
    } finally {
      navigate('/')
    }
  }

  return (
    <header className="cabecalho">
      <div className="cabecalho-linha">
        <p className="titulo">
          <Link to="/">Achados e Perdidos do CIn</Link>
        </p>
        <nav className="menu" aria-label="Conta">
          {sessao.carregando ? null : sessao.autenticado ? (
            <>
              <Link to="/meus-anuncios">Meus anúncios</Link>
              <button type="button" className="link" onClick={sair}>
                Sair
              </button>
            </>
          ) : (
            <a href={linkDeLogin(retorno)}>Entrar com a conta do CIn</a>
          )}
        </nav>
      </div>
      <p className="subtitulo">O que circula na lista achados-perdidos@cin.ufpe.br, num lugar só.</p>
    </header>
  )
}
