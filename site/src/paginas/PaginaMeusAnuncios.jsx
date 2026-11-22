// "Meus anúncios" (US-15): tudo em que a conta do CIn é autora, inclusive o que foi mandado por
// e-mail para a lista antes de conhecer o site. Três grupos na mesma tela:
//   1. mensagens retidas que abriram uma thread minha (fora do catálogo, com o motivo);
//   2. anúncios no catálogo;
//   3. anúncios que removi do catálogo (marcados, sem botão: não dá para desfazer pelo site).
// Anúncio do site cujo e-mail o worker ainda não leu na lista aparece com "ainda não foi para a
// lista" e o botão para abrir o e-mail pronto de novo (US-07).
// Os grupos 1 e 3 são as duas exceções da invariante 5: a API só os manda para o próprio autor.
// O site não filtra nem esconde nada: mostra o que GET /api/eu/itens devolver.

import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { classificarRetida, listarMeusItens, obterEmailPronto } from '../api/cliente.js'
import CartaoItem, { FaixaDoTipo } from '../componentes/CartaoItem.jsx'
import Icone from '../componentes/Icone.jsx'
import EmailPronto from '../componentes/EmailPronto.jsx'
import { telaDeLogin } from '../rotasDoLogin.js'
import { dataCompleta, tempoRelativo } from '../tempoRelativo.js'

// Motivos de retenção (shared/AGENTS.md), em português de gente.
export const MOTIVO_DA_RETENCAO = {
  fora_de_tema: 'não parecia ser sobre um objeto achado ou perdido',
  direcao_ambigua: 'não deu para saber se é um achado ou uma perda',
  confianca_baixa: 'a classificação automática ficou em dúvida',
  sem_texto_e_sem_objeto: 'a mensagem veio sem texto e sem objeto',
  classificador_indisponivel: 'a classificação automática estava fora do ar',
}

function Retida({ retida, onClassificada, onRecarregar }) {
  const [enviando, setEnviando] = useState(false)
  const [falha, setFalha] = useState(null)
  const navigate = useNavigate()

  const classificar = async (tipo) => {
    if (enviando) return
    setEnviando(true)
    setFalha(null)
    try {
      const item = await classificarRetida(retida.id, tipo)
      onClassificada()
      navigate(`/itens/${encodeURIComponent(item.id)}`)
    } catch (erro) {
      if (erro.status === 401) return navigate(telaDeLogin('/meus-anuncios', 'sessao_expirada'))
      if (erro.status === 409 || erro.status === 404) {
        setFalha('Essa mensagem já tinha sido resolvida. A lista foi atualizada.')
        onRecarregar()
      } else {
        setFalha('Não foi possível salvar. Tente de novo.')
      }
      setEnviando(false)
    }
  }

  const motivo = MOTIVO_DA_RETENCAO[retida.motivo_retencao] ?? retida.motivo_retencao ?? 'motivo não informado'

  return (
    <article className="cracha cracha-retido">
      <div className="faixa">
        <Icone nome="alerta" tamanho={16} />
        <p className="marcacao">não entrou no catálogo: {motivo}</p>
      </div>
      <div className="cracha-corpo">
        <p className="nome">{retida.descricao}</p>
        <p className="onde">
          <time dateTime={retida.data_registro} title={dataCompleta(retida.data_registro)}>
            {tempoRelativo(retida.data_registro)}
          </time>
        </p>
        <p className="pergunta">Diga o que é, e ela entra no catálogo:</p>
        <div className="botoes">
          <button type="button" className="secundario" onClick={() => classificar('achado')} disabled={enviando}>
            É um achado
          </button>
          <button type="button" className="secundario" onClick={() => classificar('perdido')} disabled={enviando}>
            É um perdido
          </button>
        </div>
        {falha && (
          <p className="alerta" role="alert">
            {falha}
          </p>
        )}
      </div>
    </article>
  )
}

function AindaNaoFoiParaALista({ item }) {
  const [estado, setEstado] = useState({ carregando: false, email: null, falha: false })
  const navigate = useNavigate()

  const abrir = async () => {
    setEstado({ carregando: true, email: null, falha: false })
    try {
      setEstado({ carregando: false, email: await obterEmailPronto(item.id), falha: false })
    } catch (erro) {
      if (erro.status === 401) return navigate(telaDeLogin('/meus-anuncios', 'sessao_expirada'))
      setEstado({ carregando: false, email: null, falha: true })
    }
  }

  return (
    <div className="pendencia-lista">
      <p className="marcacao">
        <Icone nome="carta" tamanho={16} />
        <span>ainda não foi para a lista</span>
      </p>
      {estado.email ? (
        <EmailPronto email={estado.email} id={`email-${item.id}`} />
      ) : (
        <div className="botoes">
          <button type="button" className="secundario" onClick={abrir} disabled={estado.carregando}>
            {estado.carregando ? 'Abrindo…' : 'Abrir o e-mail de novo'}
          </button>
        </div>
      )}
      {estado.falha && (
        <p className="alerta" role="alert">
          Não foi possível montar o e-mail agora. Tente de novo.
        </p>
      )}
    </div>
  )
}

function Oculto({ item }) {
  return (
    <article className={`cracha cracha-${item.tipo} cracha-oculto`}>
      <FaixaDoTipo item={{ tipo: item.tipo }}>
        <span className="marcacao marcacao-removido">
          <Icone nome="removido" tamanho={16} />
          <span>removido do catálogo</span>
        </span>
      </FaixaDoTipo>
      <div className="cracha-corpo">
        <p className="nome">{item.descricao}</p>
        <p className="onde">A remoção não pode ser desfeita pelo site.</p>
      </div>
    </article>
  )
}

function Grupo({ titulo, itens, children }) {
  if (itens.length === 0) return null
  return (
    <section className="grupo" aria-label={titulo}>
      <h2>{titulo}</h2>
      <ul className="lista-itens">
        {itens.map((item) => (
          <li key={item.id}>{children(item)}</li>
        ))}
      </ul>
    </section>
  )
}

export default function PaginaMeusAnuncios() {
  const navigate = useNavigate()
  const location = useLocation()
  const [estado, setEstado] = useState({ carregando: true, erro: null, itens: [] })
  const [versao, setVersao] = useState(0)
  const recarregar = useCallback(() => setVersao((n) => n + 1), [])

  useEffect(() => {
    const controle = new AbortController()
    listarMeusItens({ signal: controle.signal })
      .then((itens) => setEstado({ carregando: false, erro: null, itens: Array.isArray(itens) ? itens : [] }))
      .catch((erro) => {
        if (erro.name === 'AbortError') return
        if (erro.status === 401) return navigate(telaDeLogin('/meus-anuncios', 'sessao_expirada'), { replace: true })
        setEstado({ carregando: false, erro, itens: [] })
      })
    return () => controle.abort()
  }, [versao, navigate])

  const retidas = estado.itens.filter((i) => i.fora_do_catalogo)
  const ocultos = estado.itens.filter((i) => !i.fora_do_catalogo && i.oculto)
  const noCatalogo = estado.itens.filter((i) => !i.fora_do_catalogo && !i.oculto)

  return (
    <section className="meus-anuncios">
      <h1>Meus anúncios</h1>
      <p className="aviso">
        Os anúncios em que você é o autor, inclusive os que você mandou por e-mail para a lista.
      </p>
      {location.state?.aviso && <p role="status">{location.state.aviso}</p>}

      <div aria-live="polite" aria-busy={estado.carregando}>
        {estado.carregando ? (
          <p className="aviso">Carregando os seus anúncios…</p>
        ) : estado.erro ? (
          <div className="estado estado-erro" role="alert">
            <h2>Não foi possível carregar os seus anúncios agora</h2>
            <p>Tente de novo em alguns minutos.</p>
            <button type="button" onClick={recarregar}>
              Tentar de novo
            </button>
          </div>
        ) : estado.itens.length === 0 ? (
          <div className="estado">
            <h2>Você ainda não tem anúncios</h2>
            <p>
              Os que você mandar para a lista com a conta do CIn aparecem aqui depois de processados.
            </p>
            <p>
              <Link to="/">Ver o catálogo</Link>
            </p>
          </div>
        ) : (
          <>
            <Grupo titulo="Não entraram no catálogo" itens={retidas}>
              {(retida) => <Retida retida={retida} onClassificada={recarregar} onRecarregar={recarregar} />}
            </Grupo>
            <Grupo titulo="No catálogo" itens={noCatalogo}>
              {(item) => (
                <div className="com-pendencia">
                  <CartaoItem item={item} />
                  {item.origem === 'site' && !item.foi_para_a_lista && <AindaNaoFoiParaALista item={item} />}
                </div>
              )}
            </Grupo>
            <Grupo titulo="Removidos do catálogo" itens={ocultos}>
              {(item) => <Oculto item={item} />}
            </Grupo>
          </>
        )}
      </div>
    </section>
  )
}
