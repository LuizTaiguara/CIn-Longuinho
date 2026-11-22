// "Falar com quem anunciou" (SCRUM-103, US-05). A mensagem vai pela API, que encaminha por
// e-mail privado sem revelar o destino. Exige sessão do CIn: é o freio contra spam, e o e-mail
// da sessão vai como Reply-To para a resposta chegar a quem escreveu.
// Não existe campo de e-mail nesta tela, e o site não guarda endereço nenhum.

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { contatarAutor, linkDeLogin } from '../api/cliente.js'
import { useSessao } from '../hooks/useSessao.js'
import { apagarRascunho, guardarRascunho, lerRascunho } from '../rascunho.js'
import { telaDeLogin } from '../rotasDoLogin.js'

export const MINIMO = 10
export const MAXIMO = 2000

export default function Contato({ item, caminho }) {
  const sessao = useSessao()
  const navigate = useNavigate()
  const chave = `contato:${item.id}`
  const [mensagem, setMensagem] = useState(() => lerRascunho(chave)?.mensagem ?? '')
  const [estado, setEstado] = useState({ enviando: false, enviada: false, falha: null, erroCampo: null })

  if (sessao.carregando) return null

  if (!sessao.autenticado) {
    return (
      <section className="contato" aria-labelledby="titulo-contato">
        <h2 id="titulo-contato">Falar com quem anunciou</h2>
        <p>
          <a href={linkDeLogin(caminho)}>Entre com a conta do CIn para falar com quem anunciou</a>.
        </p>
      </section>
    )
  }

  if (estado.enviada) {
    return (
      <section className="contato" aria-labelledby="titulo-contato">
        <h2 id="titulo-contato">Falar com quem anunciou</h2>
        <p role="status">Mensagem enviada.</p>
      </section>
    )
  }

  const enviar = async (evento) => {
    evento.preventDefault()
    if (estado.enviando) return
    const texto = mensagem.trim()
    if (texto.length < MINIMO) {
      setEstado((e) => ({ ...e, erroCampo: `Escreva pelo menos ${MINIMO} caracteres.`, falha: null }))
      return
    }
    setEstado({ enviando: true, enviada: false, falha: null, erroCampo: null })
    try {
      await contatarAutor(item.id, texto)
      apagarRascunho(chave)
      setEstado({ enviando: false, enviada: true, falha: null, erroCampo: null })
    } catch (erro) {
      if (erro.status === 401) {
        guardarRascunho(chave, { mensagem })
        navigate(telaDeLogin(caminho, 'sessao_expirada'))
        return
      }
      const falha =
        erro.status === 400
          ? `A mensagem precisa ter entre ${MINIMO} e ${MAXIMO} caracteres.`
          : erro.status === 404
            ? 'Este anúncio não está mais disponível.'
            : 'Não foi possível enviar. Tente mais tarde.'
      setEstado({ enviando: false, enviada: false, falha, erroCampo: null })
    }
  }

  return (
    <section className="contato" aria-labelledby="titulo-contato">
      <h2 id="titulo-contato">Falar com quem anunciou</h2>
      <form className="formulario" onSubmit={enviar} noValidate>
        <p id="contato-aviso" className="aviso">
          Sua mensagem vai por e-mail para quem anunciou, e a resposta chega no seu e-mail do CIn. Você não vê
          o endereço dela.
        </p>
        <div className="campo">
          <label htmlFor="contato-mensagem">Sua mensagem</label>
          <textarea
            id="contato-mensagem"
            rows={4}
            maxLength={MAXIMO}
            value={mensagem}
            aria-describedby={`contato-aviso contato-contador${estado.erroCampo ? ' contato-erro' : ''}`}
            aria-invalid={estado.erroCampo ? true : undefined}
            onChange={(evento) => setMensagem(evento.target.value)}
          />
          <p id="contato-contador" className="contador">
            {mensagem.length} de {MAXIMO} caracteres
          </p>
          {estado.erroCampo && (
            <p className="erro-campo" id="contato-erro">
              {estado.erroCampo}
            </p>
          )}
        </div>
        {estado.falha && (
          <p className="alerta" role="alert">
            {estado.falha}
          </p>
        )}
        <div className="botoes">
          <button type="submit" disabled={estado.enviando}>
            {estado.enviando ? 'Enviando…' : 'Enviar mensagem'}
          </button>
        </div>
      </form>
    </section>
  )
}
