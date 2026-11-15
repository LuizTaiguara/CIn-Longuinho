// Página do item (SCRUM-53, US-04, US-05). Mostra o que a API devolve, do jeito que devolve:
// o texto original já vem mascarado (ou null sem sessão) e nada é mascarado ou filtrado aqui.

import { Link, useLocation, useParams } from 'react-router-dom'
import { linkDeLogin } from '../api/cliente.js'
import AcoesDoAutor from '../componentes/AcoesDoAutor.jsx'
import { ROTULO_TIPO } from '../componentes/CartaoItem.jsx'
import Contato from '../componentes/Contato.jsx'
import SeloRevisar from '../componentes/SeloRevisar.jsx'
import { useItem } from '../hooks/useItem.js'
import { useSessao } from '../hooks/useSessao.js'
import { textoDaLocalizacao, textoDaSituacao } from '../situacao.js'
import { dataCompleta, tempoRelativo } from '../tempoRelativo.js'

function TextoOriginal({ item, sessao, caminho }) {
  if (item.texto_original !== null && item.texto_original !== undefined) {
    return (
      <section className="texto-original" aria-labelledby="titulo-texto-original">
        <h2 id="titulo-texto-original">Texto original</h2>
        <p className="aviso">Telefones e e-mails aparecem mascarados.</p>
        <pre>{item.texto_original}</pre>
      </section>
    )
  }
  // Com sessão e sem texto: item cadastrado pelo site, que não tem e-mail original. Nada a mostrar.
  if (sessao.carregando || sessao.autenticado) return null
  return (
    <section className="texto-original" aria-labelledby="titulo-texto-original">
      <h2 id="titulo-texto-original">Texto original</h2>
      <p>
        <a href={linkDeLogin(caminho)}>Entre com a conta do CIn</a> para ler o anúncio completo.
      </p>
    </section>
  )
}

export default function PaginaItem() {
  const { id } = useParams()
  const location = useLocation()
  const sessao = useSessao()
  const { carregando, erro, item, naoEncontrado, tentarDeNovo, trocarItem } = useItem(id)
  const voltar = `/${location.state?.voltar ?? ''}`

  const linkVoltar = (
    <p className="voltar">
      <Link to={voltar}>← Voltar ao catálogo</Link>
    </p>
  )

  if (carregando) {
    return (
      <section aria-busy="true">
        {linkVoltar}
        <p className="aviso">Carregando o anúncio…</p>
      </section>
    )
  }

  // Oculto, retido ou inexistente: a mesma mensagem, sem dizer qual dos três (US-09, invariante 5).
  if (naoEncontrado) {
    return (
      <section className="estado">
        <h1>Este anúncio não está disponível</h1>
        <p>O link pode estar errado, ou o anúncio saiu do catálogo.</p>
        <p>
          <Link to="/">Ver o catálogo</Link>
        </p>
      </section>
    )
  }

  if (erro) {
    return (
      <section className="estado estado-erro" role="alert">
        <h1>Não foi possível abrir o anúncio agora</h1>
        <p>O catálogo está temporariamente fora do ar. Tente de novo em alguns minutos.</p>
        <button type="button" onClick={tentarDeNovo}>
          Tentar de novo
        </button>
      </section>
    )
  }

  const localizacao = textoDaLocalizacao(item)

  return (
    <article className="detalhe-item">
      {linkVoltar}
      <p className="etiquetas">
        <span className={`tipo tipo-${item.tipo}`}>{ROTULO_TIPO[item.tipo] ?? item.tipo}</span>
        {item.revisar && <SeloRevisar />}
      </p>
      <h1>{item.descricao}</h1>

      {item.foto_url && <img className="foto" src={item.foto_url} alt={`Foto do objeto: ${item.descricao}`} />}

      <dl className="dados">
        <dt>{item.tipo === 'perdido' ? 'Onde foi perdido' : 'Onde foi achado'}</dt>
        <dd>{item.local.length ? item.local.join(', ') : 'Local não informado'}</dd>

        <dt>Anunciado</dt>
        <dd>
          <time dateTime={item.data_registro} title={dataCompleta(item.data_registro)}>
            {tempoRelativo(item.data_registro)}
          </time>{' '}
          ({dataCompleta(item.data_registro)})
        </dd>

        <dt>Situação</dt>
        <dd className={`situacao situacao-${item.situacao}`}>
          <span title={item.data_situacao ? `Desde ${dataCompleta(item.data_situacao)}` : undefined}>
            {textoDaSituacao(item)}
          </span>
        </dd>

        {localizacao && (
          <>
            <dt>Onde está agora</dt>
            <dd>{localizacao}</dd>
          </>
        )}
      </dl>

      <TextoOriginal item={item} sessao={sessao} caminho={location.pathname} />

      {/* Só esconde os botões: quem recusa de verdade é a API, com 403. */}
      {item.pode_gerir ? (
        <AcoesDoAutor item={item} onItemMudou={trocarItem} />
      ) : (
        <Contato item={item} caminho={location.pathname} />
      )}
    </article>
  )
}
