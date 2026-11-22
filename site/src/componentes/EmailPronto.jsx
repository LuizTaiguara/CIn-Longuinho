// O e-mail pronto para a lista (US-07): "Abrir no meu e-mail", "Abrir no Gmail" e o texto para
// copiar. Usado na confirmação do cadastro e no "Abrir o e-mail de novo" de "Meus anúncios".
// A pessoa revisa e envia da própria conta: as respostas chegam a ela.

import { useRef, useState } from 'react'
import { linkGmail, linkMailto, textoParaCopiar } from '../emailPronto.js'

export default function EmailPronto({ email, id = 'email-pronto' }) {
  const campo = useRef(null)
  const [copiado, setCopiado] = useState(null)
  const texto = textoParaCopiar(email)

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(texto)
      setCopiado('Texto copiado.')
    } catch {
      // Sem acesso à área de transferência: seleciona o texto para a pessoa copiar.
      campo.current?.select()
      setCopiado('Não deu para copiar sozinho: o texto está selecionado, copie com Ctrl+C.')
    }
  }

  return (
    <div className="email-pronto">
      <p className="aviso">
        Revise o texto antes de enviar e mantenha o código entre colchetes no assunto: é por ele que o
        anúncio é reconhecido quando chega à lista.
      </p>
      <div className="botoes">
        <a className="botao" href={linkMailto(email)}>
          Abrir no meu e-mail
        </a>
        <a className="botao botao-secundario" href={linkGmail(email)} target="_blank" rel="noopener noreferrer">
          Abrir no Gmail
        </a>
      </div>
      <div className="campo">
        <label htmlFor={`${id}-texto`}>Ou copie o texto e envie para {email.para}</label>
        <textarea id={`${id}-texto`} ref={campo} readOnly rows={Math.min(Math.max(texto.split('\n').length + 3, 8), 24)} value={texto} />
      </div>
      <div className="botoes">
        <button type="button" className="secundario" onClick={copiar}>
          Copiar
        </button>
      </div>
      {copiado && <p role="status">{copiado}</p>}
    </div>
  )
}
