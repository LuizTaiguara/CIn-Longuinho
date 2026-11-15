// Cadastro pelo site (SCRUM-55, US-06). Exige a conta do CIn (a rota passa por ExigeSessao).
// Achado pergunta onde o objeto está agora; perdido não pergunta, porque quem perdeu não sabe.
// O item entra direto no catálogo, sem classificação: os dados já vêm estruturados.

import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { cadastrarItem, enviarFoto } from '../api/cliente.js'
import CampoLocais, { LOCAIS_VAZIOS, locaisEscolhidos } from '../componentes/CampoLocais.jsx'
import CampoLocalizacao from '../componentes/CampoLocalizacao.jsx'
import { useLocais } from '../hooks/useCatalogo.js'
import { apagarRascunho, guardarRascunho, lerRascunho } from '../rascunho.js'
import { telaDeLogin } from '../rotasDoLogin.js'

export const FORMATOS_DE_FOTO = ['image/jpeg', 'image/png', 'image/webp']
export const LIMITE_DA_FOTO = 5 * 1024 * 1024
const CHAVE_DO_RASCUNHO = 'cadastro'

const FORMULARIO_VAZIO = {
  tipo: '',
  descricao: '',
  locais: LOCAIS_VAZIOS,
  localizacao: { localizacao: '', setor: '' },
}

// A ordem dos campos na tela, para levar o foco ao primeiro com erro.
const ORDEM_DOS_CAMPOS = [
  ['tipo', 'cadastro-tipo'],
  ['descricao', 'cadastro-descricao'],
  ['locais', 'cadastro-locais'],
  ['localizacao', 'cadastro-localizacao'],
  ['setor', 'cadastro-localizacao-setor'],
  ['foto', 'cadastro-foto'],
]

export function validarFoto(arquivo) {
  if (!arquivo) return null
  if (!FORMATOS_DE_FOTO.includes(arquivo.type)) return 'A foto precisa ser JPEG, PNG ou WebP. Escolha outra, ou publique sem foto.'
  if (arquivo.size > LIMITE_DA_FOTO) return 'A foto passa de 5 MB. Escolha uma menor, ou publique sem foto.'
  return null
}

function validar(form) {
  const erros = {}
  if (!form.tipo) erros.tipo = 'Escolha se você achou ou perdeu o objeto.'
  if (form.descricao.trim().length < 5) erros.descricao = 'Descreva o objeto com pelo menos 5 letras.'
  if (locaisEscolhidos(form.locais).length === 0) erros.locais = 'Marque pelo menos um local.'
  if (form.tipo === 'achado') {
    if (!form.localizacao.localizacao) erros.localizacao = 'Diga onde o objeto está agora.'
    else if (form.localizacao.localizacao === 'com um setor' && !form.localizacao.setor.trim()) {
      erros.setor = 'Diga qual setor.'
    }
  }
  return erros
}

function corpoDoCadastro(form) {
  const corpo = { tipo: form.tipo, descricao: form.descricao.trim(), local: locaisEscolhidos(form.locais) }
  if (form.tipo === 'achado') {
    corpo.localizacao = form.localizacao.localizacao
    if (corpo.localizacao === 'com um setor') corpo.setor = form.localizacao.setor.trim()
  }
  return corpo
}

function mensagemDaFoto(erro) {
  if (erro.codigo === 'FOTO_GRANDE' || erro.status === 413) return 'a foto passa de 5 MB'
  if (erro.codigo === 'FOTO_INVALIDA') return 'a foto precisa ser JPEG, PNG ou WebP'
  return 'a foto não pôde ser enviada agora'
}

function Confirmacao({ item, avisoFoto }) {
  return (
    <section className="confirmacao-cadastro" aria-labelledby="titulo-confirmacao">
      <h1 id="titulo-confirmacao" tabIndex={-1}>
        Anúncio publicado
      </h1>
      <p>
        Seu anúncio já está no catálogo: <Link to={`/itens/${encodeURIComponent(item.id)}`}>ver o anúncio</Link>.
      </p>
      {avisoFoto && (
        <p className="alerta" role="alert">
          O anúncio foi publicado sem foto: {avisoFoto}. Você pode corrigir o resto do anúncio na página dele.
        </p>
      )}
    </section>
  )
}

export default function PaginaCadastrar() {
  const navigate = useNavigate()
  const locais = useLocais()
  const [rascunho] = useState(() => lerRascunho(CHAVE_DO_RASCUNHO))
  const [form, setForm] = useState(() => (rascunho ? { ...FORMULARIO_VAZIO, ...rascunho } : FORMULARIO_VAZIO))
  const [foto, setFoto] = useState(null)
  const [erros, setErros] = useState({})
  const [falha, setFalha] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [confirmacao, setConfirmacao] = useState(null)
  // Trava síncrona contra clique duplo: o estado do React só muda no próximo render.
  const travado = useRef(false)

  const mudar = (campo) => (valor) => setForm((anterior) => ({ ...anterior, [campo]: valor }))

  const escolherFoto = (evento) => {
    const arquivo = evento.target.files?.[0] ?? null
    const erro = validarFoto(arquivo)
    setErros((anteriores) => ({ ...anteriores, foto: erro ?? undefined }))
    if (erro) {
      // Foto recusada não apaga nada do resto do formulário.
      evento.target.value = ''
      setFoto(null)
    } else {
      setFoto(arquivo)
    }
  }

  const focarPrimeiroErro = (encontrados) => {
    const primeiro = ORDEM_DOS_CAMPOS.find(([campo]) => encontrados[campo])
    if (primeiro) document.getElementById(primeiro[1])?.focus()
  }

  const enviar = async (evento) => {
    evento.preventDefault()
    if (travado.current) return
    // Uma foto recusada já foi tirada do campo: o aviso continua na tela e o anúncio segue sem ela.
    const novosErros = validar(form)
    setErros(erros.foto ? { ...novosErros, foto: erros.foto } : novosErros)
    const bloqueiam = novosErros
    setFalha(null)
    if (Object.keys(bloqueiam).length) return focarPrimeiroErro(bloqueiam)

    travado.current = true
    setEnviando(true)
    let item
    try {
      item = await cadastrarItem(corpoDoCadastro(form))
    } catch (erro) {
      travado.current = false
      setEnviando(false)
      if (erro.status === 401) {
        // A foto não dá para guardar no navegador; o resto volta quando a pessoa entrar de novo.
        guardarRascunho(CHAVE_DO_RASCUNHO, form)
        return navigate(telaDeLogin('/cadastrar', 'sessao_expirada'))
      }
      if (erro.codigo === 'LOCALIZACAO_OBRIGATORIA') {
        const doServidor = { localizacao: 'Diga onde o objeto está agora.' }
        setErros(doServidor)
        return focarPrimeiroErro(doServidor)
      }
      setFalha(
        erro.status === 400
          ? 'A API não aceitou os dados. Confira os campos e tente de novo.'
          : 'Não foi possível salvar. Tente de novo.',
      )
      return
    }

    apagarRascunho(CHAVE_DO_RASCUNHO)
    let avisoFoto = null
    if (foto) {
      try {
        item = await enviarFoto(item.id, foto)
      } catch (erro) {
        avisoFoto = mensagemDaFoto(erro)
      }
    }
    setConfirmacao({ item, avisoFoto })
    setEnviando(false)
  }

  if (confirmacao) return <Confirmacao {...confirmacao} />

  const achado = form.tipo === 'achado'
  const perdido = form.tipo === 'perdido'

  return (
    <section className="cadastro">
      <h1>Cadastrar um achado ou uma perda</h1>
      {rascunho && <p role="status">Recuperamos o que você tinha preenchido antes de a sessão expirar.</p>}

      <form className="formulario" onSubmit={enviar} noValidate>
        <fieldset
          className="campo-grupo"
          aria-invalid={erros.tipo ? true : undefined}
          aria-describedby={erros.tipo ? 'cadastro-tipo-erro' : undefined}
        >
          <legend>O que aconteceu?</legend>
          <div className="opcoes">
            <label className="opcao">
              <input
                type="radio"
                id="cadastro-tipo"
                name="tipo"
                value="achado"
                checked={achado}
                onChange={() => mudar('tipo')('achado')}
              />
              Achei um objeto
            </label>
            <label className="opcao">
              <input type="radio" name="tipo" value="perdido" checked={perdido} onChange={() => mudar('tipo')('perdido')} />
              Perdi um objeto
            </label>
          </div>
          {erros.tipo && (
            <p className="erro-campo" id="cadastro-tipo-erro">
              {erros.tipo}
            </p>
          )}
        </fieldset>

        <div className="campo">
          <label htmlFor="cadastro-descricao">Descrição do objeto</label>
          <textarea
            id="cadastro-descricao"
            rows={3}
            placeholder="Ex.: garrafa térmica azul com adesivo do CIn"
            value={form.descricao}
            aria-invalid={erros.descricao ? true : undefined}
            aria-describedby={erros.descricao ? 'cadastro-descricao-erro' : undefined}
            onChange={(evento) => mudar('descricao')(evento.target.value)}
          />
          {erros.descricao && (
            <p className="erro-campo" id="cadastro-descricao-erro">
              {erros.descricao}
            </p>
          )}
        </div>

        <CampoLocais
          id="cadastro-locais"
          legenda={perdido ? 'Onde você perdeu? Pode marcar mais de um.' : 'Onde você achou?'}
          locais={locais}
          valor={form.locais}
          onMudar={mudar('locais')}
          erro={erros.locais}
        />

        {/* Só no achado: quem perdeu não sabe onde o objeto está. */}
        {achado && (
          <CampoLocalizacao
            id="cadastro-localizacao"
            valor={form.localizacao}
            onMudar={mudar('localizacao')}
            erro={erros.localizacao}
            erroSetor={erros.setor}
          />
        )}

        <div className="campo">
          <label htmlFor="cadastro-foto">Foto (opcional): JPEG, PNG ou WebP, até 5 MB</label>
          <input
            id="cadastro-foto"
            type="file"
            accept={FORMATOS_DE_FOTO.join(',')}
            aria-invalid={erros.foto ? true : undefined}
            aria-describedby={erros.foto ? 'cadastro-foto-erro' : undefined}
            onChange={escolherFoto}
          />
          {erros.foto && (
            <p className="erro-campo" id="cadastro-foto-erro">
              {erros.foto}
            </p>
          )}
        </div>

        {falha && (
          <p className="alerta" role="alert">
            {falha}
          </p>
        )}

        <div className="botoes">
          <button type="submit" disabled={enviando}>
            {enviando ? 'Publicando…' : 'Publicar anúncio'}
          </button>
        </div>
      </form>
    </section>
  )
}
