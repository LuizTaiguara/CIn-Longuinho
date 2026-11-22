// Ações de quem anunciou, na página do item (US-15): corrigir, marcar como devolvido e remover
// do catálogo. Só aparecem com `pode_gerir = true`, mas quem nega de verdade é a API (403).
//
// Sessão expirada no meio da correção: o que foi digitado fica guardado no navegador, a pessoa
// passa pelo login e volta a este item com o formulário reaberto (US-15, casos de falha).

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { corrigirItem, encerrarItem, ocultarItem } from '../api/cliente.js'
import { useLocais } from '../hooks/useCatalogo.js'
import { apagarRascunho, guardarRascunho, lerRascunho } from '../rascunho.js'
import { telaDeLogin } from '../rotasDoLogin.js'
import CampoLocais, { locaisEscolhidos, valorDosLocais } from './CampoLocais.jsx'
import CampoLocalizacao from './CampoLocalizacao.jsx'

const chaveDoRascunho = (id) => `correcao:${id}`

function formularioDoItem(item) {
  return {
    descricao: item.descricao,
    locais: valorDosLocais(item.local),
    localizacao: { localizacao: item.localizacao ?? '', setor: item.setor ?? '' },
  }
}

const mesmaLista = (a, b) => a.length === b.length && a.every((x, n) => x === b[n])

// Só o que mudou vai para a API: cada mudança vira um evento, e nada que não mudou é "declarado".
export function mudancasDaCorrecao(item, form) {
  const mudancas = {}
  const descricao = form.descricao.trim()
  if (descricao !== item.descricao) mudancas.descricao = descricao
  const local = locaisEscolhidos(form.locais)
  if (!mesmaLista(local, item.local)) mudancas.local = local
  if (item.tipo === 'achado' && form.localizacao.localizacao) {
    const { localizacao } = form.localizacao
    const setor = form.localizacao.setor.trim()
    const mudouSetor = localizacao === 'com um setor' && setor !== (item.setor ?? '')
    if (localizacao !== item.localizacao || mudouSetor) {
      mudancas.localizacao = localizacao
      if (localizacao === 'com um setor') mudancas.setor = setor
    }
  }
  return mudancas
}

function validar(item, form, mudancas) {
  const erros = {}
  if (form.descricao.trim().length < 5) erros.descricao = 'Descreva o objeto com pelo menos 5 letras.'
  if ('local' in mudancas && mudancas.local.length === 0) erros.locais = 'Marque pelo menos um local.'
  if (item.tipo === 'achado' && form.localizacao.localizacao === 'com um setor' && !form.localizacao.setor.trim()) {
    erros.setor = 'Diga qual setor.'
  }
  return erros
}

function mensagemDeFalha(erro, verbo = 'salvar') {
  if (erro.status === 403) return 'Só quem anunciou pode mudar este anúncio.'
  if (erro.status === 404) return 'Este anúncio não está mais disponível.'
  if (erro.status === 400) return 'A API não aceitou os dados. Confira os campos e tente de novo.'
  return `Não foi possível ${verbo}. Tente de novo.`
}

function FormularioCorrecao({ item, inicial, recuperado, onSalvo, onCancelar, onSessaoExpirada }) {
  const locais = useLocais()
  const [form, setForm] = useState(inicial)
  const [erros, setErros] = useState({})
  const [falha, setFalha] = useState(null)
  const [enviando, setEnviando] = useState(false)

  const mudar = (campo) => (valor) => setForm((anterior) => ({ ...anterior, [campo]: valor }))

  const enviar = async (evento) => {
    evento.preventDefault()
    if (enviando) return
    const mudancas = mudancasDaCorrecao(item, form)
    const novosErros = validar(item, form, mudancas)
    setErros(novosErros)
    setFalha(null)
    if (Object.keys(novosErros).length) return
    if (Object.keys(mudancas).length === 0) return onCancelar()

    setEnviando(true)
    try {
      const atualizado = await corrigirItem(item.id, mudancas)
      onSalvo(atualizado)
    } catch (erro) {
      if (erro.status === 401) return onSessaoExpirada(form)
      setFalha(mensagemDeFalha(erro))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={enviar} noValidate aria-labelledby="titulo-corrigir">
      <h2 id="titulo-corrigir">Corrigir o anúncio</h2>
      {recuperado && <p role="status">Recuperamos o que você tinha escrito antes de a sessão expirar.</p>}

      <div className="campo">
        <label htmlFor="corrigir-descricao">Descrição</label>
        <textarea
          id="corrigir-descricao"
          rows={3}
          value={form.descricao}
          aria-invalid={erros.descricao ? true : undefined}
          aria-describedby={erros.descricao ? 'corrigir-descricao-erro' : undefined}
          onChange={(evento) => mudar('descricao')(evento.target.value)}
        />
        {erros.descricao && (
          <p className="erro-campo" id="corrigir-descricao-erro">
            {erros.descricao}
          </p>
        )}
      </div>

      <CampoLocais
        id="corrigir-locais"
        legenda={item.tipo === 'perdido' ? 'Onde foi perdido' : 'Onde foi achado'}
        locais={locais}
        valor={form.locais}
        onMudar={mudar('locais')}
        erro={erros.locais}
      />

      {item.tipo === 'achado' && (
        <CampoLocalizacao
          id="corrigir-localizacao"
          valor={form.localizacao}
          onMudar={mudar('localizacao')}
          erroSetor={erros.setor}
        />
      )}

      {falha && (
        <p className="alerta" role="alert">
          {falha}
        </p>
      )}

      <div className="botoes">
        <button type="submit" disabled={enviando}>
          {enviando ? 'Salvando…' : 'Salvar correção'}
        </button>
        <button type="button" className="secundario" onClick={onCancelar} disabled={enviando}>
          Cancelar
        </button>
      </div>
    </form>
  )
}

function Confirmacao({ pergunta, confirmar, onConfirmar, onCancelar, enviando }) {
  return (
    <div className="confirmacao" role="group" aria-label="Confirmação">
      <p>{pergunta}</p>
      <div className="botoes">
        <button type="button" onClick={onConfirmar} disabled={enviando}>
          {enviando ? 'Enviando…' : confirmar}
        </button>
        <button type="button" className="secundario" onClick={onCancelar} disabled={enviando}>
          Cancelar
        </button>
      </div>
    </div>
  )
}

export default function AcoesDoAutor({ item, onItemMudou }) {
  const navigate = useNavigate()
  const chave = chaveDoRascunho(item.id)
  // Voltando do login com um rascunho guardado: o formulário já abre com ele.
  const [rascunho] = useState(() => lerRascunho(chave))
  const [modo, setModo] = useState(rascunho ? 'corrigir' : null)
  const [enviando, setEnviando] = useState(false)
  const [aviso, setAviso] = useState(null)
  const [falha, setFalha] = useState(null)

  const sessaoExpirada = (form) => {
    if (form) guardarRascunho(chave, form)
    navigate(telaDeLogin(`/itens/${item.id}`, 'sessao_expirada'))
  }

  const fechar = () => {
    apagarRascunho(chave)
    setModo(null)
  }

  const executar = async (acao, aoTerminar) => {
    if (enviando) return
    setEnviando(true)
    setFalha(null)
    try {
      aoTerminar(await acao(item.id))
    } catch (erro) {
      if (erro.status === 401) return sessaoExpirada(null)
      setFalha(mensagemDeFalha(erro, 'concluir'))
    } finally {
      setEnviando(false)
    }
  }

  const encerrar = () =>
    executar(encerrarItem, (atualizado) => {
      setModo(null)
      setAviso('Anúncio marcado como devolvido.')
      onItemMudou(atualizado)
    })

  const ocultar = () =>
    executar(ocultarItem, () =>
      navigate('/meus-anuncios', { state: { aviso: 'Anúncio removido do catálogo.' } }),
    )

  return (
    <section className="acoes-do-autor" aria-labelledby="titulo-acoes">
      <h2 id="titulo-acoes">Este anúncio é seu</h2>
      {aviso && <p role="status">{aviso}</p>}
      {falha && (
        <p className="alerta" role="alert">
          {falha}
        </p>
      )}

      {modo === 'corrigir' ? (
        <FormularioCorrecao
          item={item}
          inicial={rascunho ?? formularioDoItem(item)}
          recuperado={Boolean(rascunho)}
          onSalvo={(atualizado) => {
            fechar()
            setAviso('Correção salva.')
            onItemMudou(atualizado)
          }}
          onCancelar={fechar}
          onSessaoExpirada={sessaoExpirada}
        />
      ) : modo === 'encerrar' ? (
        <Confirmacao
          pergunta="Confirma que o objeto foi devolvido? O anúncio passa a encerrado, e isso não volta atrás."
          confirmar="Sim, foi devolvido"
          onConfirmar={encerrar}
          onCancelar={() => setModo(null)}
          enviando={enviando}
        />
      ) : modo === 'ocultar' ? (
        <Confirmacao
          pergunta="O anúncio sai do catálogo e a remoção não pode ser desfeita pelo site. Ele continua em Meus anúncios, marcado como removido. Remover mesmo assim?"
          confirmar="Sim, remover do catálogo"
          onConfirmar={ocultar}
          onCancelar={() => setModo(null)}
          enviando={enviando}
        />
      ) : (
        <div className="botoes">
          <button type="button" className="secundario" onClick={() => { setAviso(null); setModo('corrigir') }}>
            Corrigir
          </button>
          {item.situacao !== 'encerrado' && (
            <button type="button" onClick={() => { setAviso(null); setModo('encerrar') }}>
              Marcar como devolvido
            </button>
          )}
          <button type="button" className="perigo" onClick={() => { setAviso(null); setModo('ocultar') }}>
            Remover do catálogo
          </button>
        </div>
      )}
    </section>
  )
}
