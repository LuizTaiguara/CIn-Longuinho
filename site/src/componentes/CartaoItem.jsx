// Um item na lista do catálogo (SCRUM-97, US-04): tipo, descrição, local(is), data e situação.
// A descrição é o link para a página do item.
//
// Desenho (SCRUM-47, grade de Crouwel): cada anúncio é uma linha da grade. A primeira coluna diz o
// tipo e a idade; a segunda traz o objeto, o local e a situação. Quem tem foto ganha o botão
// "Ver foto": a linha abre e mostra a foto em largura total. Sem foto, nada de quadrado vazio.

import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { textoDaLocalizacao, textoDaSituacao } from '../situacao.js'
import { dataCompleta, tempoRelativo } from '../tempoRelativo.js'
import Icone from './Icone.jsx'
import SeloRevisar from './SeloRevisar.jsx'

export const ROTULO_TIPO = { achado: 'Achado', perdido: 'Perdido' }

// A célula do tipo, igual na lista, na página do item e em "Meus anúncios".
export function FaixaDoTipo({ item, children }) {
  return (
    <p className="faixa">
      <span className="tipo">
        <Icone nome={item.tipo} tamanho={16} />
        <span>{ROTULO_TIPO[item.tipo] ?? item.tipo}</span>
      </span>
      {item.revisar && <SeloRevisar />}
      {children}
    </p>
  )
}

export function classesDoAnuncio(item) {
  return `anuncio anuncio-${item.tipo}${item.situacao === 'encerrado' ? ' anuncio-encerrado' : ''}`
}

export default function CartaoItem({ item }) {
  const { search } = useLocation()
  const [fotoAberta, setFotoAberta] = useState(false)
  const localizacao = textoDaLocalizacao(item)
  const idFoto = `foto-${item.id}`

  return (
    <article className={`${classesDoAnuncio(item)}${fotoAberta ? ' anuncio-com-foto-aberta' : ''}`}>
      <FaixaDoTipo item={item}>
        <time className="quando" dateTime={item.data_registro} title={dataCompleta(item.data_registro)}>
          {tempoRelativo(item.data_registro)}
        </time>
      </FaixaDoTipo>
      <div className="anuncio-corpo">
        <h2 className="nome">
          {/* Guarda a busca atual para o "Voltar ao catálogo" da página do item não perder os filtros. */}
          <Link to={`/itens/${encodeURIComponent(item.id)}`} state={{ voltar: search }}>
            {item.descricao}
          </Link>
        </h2>
        <p className="onde">{item.local.length ? item.local.join(', ') : 'Local não informado'}</p>
        <p className={`situacao situacao-${item.situacao}`}>
          <Icone nome={item.situacao} tamanho={14} />
          <span>
            <span className="visualmente-oculto">Situação: </span>
            <span title={item.data_situacao ? `Desde ${dataCompleta(item.data_situacao)}` : undefined}>
              {textoDaSituacao(item)}
            </span>
            {localizacao && <span className="localizacao"> · {localizacao}</span>}
          </span>
        </p>
      </div>
      {/* Botão da foto: abaixo da situação no celular; dentro da célula do objeto no desktop.
          Sem foto, não aparece nada. */}
      <div className="celula-foto">
        {item.foto_url && (
          <button
            type="button"
            className="botao-foto"
            aria-expanded={fotoAberta}
            aria-controls={idFoto}
            onClick={() => setFotoAberta((aberta) => !aberta)}
          >
            <Icone nome="foto" tamanho={16} />
            {fotoAberta ? 'Fechar foto' : 'Ver foto'}
          </button>
        )}
      </div>
      {item.foto_url && (
        // A imagem só é baixada quando a pessoa pede: no celular, dado custa.
        <div className="painel-foto" id={idFoto} hidden={!fotoAberta}>
          {fotoAberta && <img src={item.foto_url} alt={`Foto do objeto: ${item.descricao}`} />}
        </div>
      )}
    </article>
  )
}
