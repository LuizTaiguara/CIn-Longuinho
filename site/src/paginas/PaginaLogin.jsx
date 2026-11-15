// Tela /login (US-15, ADR-010). Explica para que serve o login e manda à API, que fala com o
// Google. A API volta para cá com ?erro=... quando o login não dá certo.

import { Link, useSearchParams } from 'react-router-dom'
import { linkDeLogin } from '../api/cliente.js'
import { useSessao } from '../hooks/useSessao.js'
import { retornoSeguro } from '../rotasDoLogin.js'

// Códigos que a API manda em /login?erro=... (api/rotas/auth.py), mais `sessao_expirada`, que é do site.
const MENSAGENS_DE_ERRO = {
  conta_fora_do_cin: 'Só contas @cin.ufpe.br podem gerir anúncios. O catálogo continua aberto para leitura.',
  recusado: 'O login foi cancelado. O catálogo continua aberto para leitura.',
  estado_invalido: 'O login não pôde ser concluído. Tente entrar de novo.',
  login_indisponivel:
    'O login com o Google está indisponível agora. O catálogo continua aberto para leitura; tente entrar mais tarde.',
  sessao_expirada:
    'Sua sessão expirou. Entre de novo para continuar: o que você tinha escrito ficou guardado neste navegador.',
}
const ERRO_GENERICO = 'Não foi possível entrar agora. Tente de novo em alguns minutos. O catálogo continua aberto para leitura.'

export default function PaginaLogin() {
  const [params] = useSearchParams()
  const sessao = useSessao()
  const erro = params.get('erro')
  const retorno = retornoSeguro(params.get('retorno'))

  return (
    <section className="estado tela-login">
      <h1>Entrar com a conta do CIn</h1>

      {erro && (
        <p className="alerta" role="alert">
          {MENSAGENS_DE_ERRO[erro] ?? ERRO_GENERICO}
        </p>
      )}

      {sessao.autenticado ? (
        <p>
          Você já entrou{sessao.nome ? ` como ${sessao.nome}` : ''}. <Link to={retorno}>Continuar</Link>
        </p>
      ) : (
        <>
          <p>
            Para ler o catálogo não é preciso entrar. O login serve para gerir os seus anúncios: corrigir,
            marcar como devolvido, remover e cadastrar pelo site.
          </p>
          <p>
            Só contas <strong>@cin.ufpe.br</strong>. A senha fica com o Google: o site não pede nem guarda senha.
          </p>
          <p>
            <a className="botao" href={linkDeLogin(retorno)}>
              Entrar com a conta do CIn
            </a>
          </p>
        </>
      )}
    </section>
  )
}
