// Telas que só fazem sentido com a conta do CIn ("Meus anúncios", "Cadastrar").
// Sem sessão, manda para /login com o caminho de volta. Isto só organiza a navegação:
// quem protege os dados é a API, que responde 401.

import { Navigate, useLocation } from 'react-router-dom'
import { useSessao } from '../hooks/useSessao.js'
import { telaDeLogin } from '../rotasDoLogin.js'

export default function ExigeSessao({ children }) {
  const sessao = useSessao()
  const { pathname, search } = useLocation()

  if (sessao.carregando) return <p className="aviso">Carregando…</p>
  if (!sessao.autenticado) return <Navigate to={telaDeLogin(`${pathname}${search}`)} replace />
  return children
}
