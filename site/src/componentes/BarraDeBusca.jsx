// Busca por termo e filtros do catálogo (SCRUM-98, US-04).
// Lista única: achados e perdidos juntos por padrão, e o filtro de tipo refina (decisão do PO, 25/10).
// O dropdown de locais usa o vocabulário fechado do F-07 vindo da API, não texto livre.

import { useEffect, useState } from 'react'
import { FILTROS_VAZIOS, SITUACOES, temFiltroAtivo } from '../filtros.js'

const ROTULO_SITUACAO = { aberto: 'Aberto', reivindicado: 'Reivindicado', encerrado: 'Encerrado' }

export default function BarraDeBusca({ filtros, locais, onMudar }) {
  // O termo é editado localmente e só vai para a URL ao enviar, para não disparar
  // uma busca a cada tecla.
  const [texto, setTexto] = useState(filtros.texto)
  useEffect(() => setTexto(filtros.texto), [filtros.texto])

  const mudar = (campo) => (evento) => onMudar({ ...filtros, [campo]: evento.target.value })

  const enviar = (evento) => {
    evento.preventDefault()
    onMudar({ ...filtros, texto: texto.trim() })
  }

  // Um local da URL que não está na lista (ex.: link antigo) continua aparecendo como opção,
  // para o select não esconder um filtro que está ativo.
  const opcoesDeLocal = locais.lista.map((local) => local.nome)
  if (filtros.local && !opcoesDeLocal.includes(filtros.local)) opcoesDeLocal.unshift(filtros.local)

  return (
    <form className="barra-de-busca" role="search" onSubmit={enviar}>
      <div className="campo campo-texto">
        <label htmlFor="busca-texto">O que você procura?</label>
        <div className="linha">
          <input
            id="busca-texto"
            type="search"
            placeholder="Ex.: garrafa azul, carregador, chave"
            value={texto}
            onChange={(evento) => setTexto(evento.target.value)}
          />
          <button type="submit">Buscar</button>
        </div>
      </div>

      <div className="campo">
        <label htmlFor="filtro-local">Local</label>
        <select
          id="filtro-local"
          value={filtros.local}
          onChange={mudar('local')}
          disabled={locais.carregando || (locais.erro && opcoesDeLocal.length === 0)}
        >
          <option value="">
            {locais.carregando ? 'Carregando locais…' : locais.erro ? 'Locais indisponíveis' : 'Todos os locais'}
          </option>
          {opcoesDeLocal.map((nome) => (
            <option key={nome} value={nome}>
              {nome}
            </option>
          ))}
        </select>
      </div>

      <div className="campo">
        <label htmlFor="filtro-tipo">Tipo</label>
        <select id="filtro-tipo" value={filtros.tipo} onChange={mudar('tipo')}>
          <option value="">Achados e perdidos</option>
          <option value="achado">Só achados</option>
          <option value="perdido">Só perdidos</option>
        </select>
      </div>

      <div className="campo">
        <label htmlFor="filtro-situacao">Situação</label>
        <select id="filtro-situacao" value={filtros.situacao} onChange={mudar('situacao')}>
          <option value="">Todas</option>
          {SITUACOES.map((situacao) => (
            <option key={situacao} value={situacao}>
              {ROTULO_SITUACAO[situacao]}
            </option>
          ))}
        </select>
      </div>

      {temFiltroAtivo(filtros) && (
        <button type="button" className="limpar" onClick={() => onMudar({ ...FILTROS_VAZIOS })}>
          Limpar filtros
        </button>
      )}
    </form>
  )
}
