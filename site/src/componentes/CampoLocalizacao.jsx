// "Onde o objeto está agora" (US-06, US-15): só no achado. Os cinco valores do contrato.
// "Com um setor" abre o nome do setor, em texto livre.
//
// Valor: { localizacao: string, setor: string }

export const OPCOES_DE_LOCALIZACAO = [
  ['com quem achou', 'Comigo (com quem achou)'],
  ['no local', 'Deixei no local onde achei'],
  ['com um setor', 'Entreguei a um setor'],
  ['caixa do bloco A/E', 'Na caixa do bloco A/E'],
  ['devolvido', 'Já devolvi ao dono'],
]

// Sugestões, não lista fechada: a pessoa pode escrever outro setor.
// Só a SecGrad: a portaria e a Gerinfra disseram que não recebem objetos (ARQUITETURA §1).
export const SUGESTOES_DE_SETOR = ['SecGrad']

export default function CampoLocalizacao({ id, valor, onMudar, erro, erroSetor }) {
  const idErro = `${id}-erro`
  return (
    <fieldset className="campo-grupo" aria-describedby={erro ? idErro : undefined} aria-invalid={erro ? true : undefined}>
      <legend>Onde o objeto está agora?</legend>
      <div className="opcoes">
        {OPCOES_DE_LOCALIZACAO.map(([codigo, rotulo], n) => (
          <label key={codigo} className="opcao">
            <input
              type="radio"
              id={n === 0 ? id : undefined}
              name={id}
              value={codigo}
              checked={valor.localizacao === codigo}
              onChange={() => onMudar({ ...valor, localizacao: codigo })}
            />
            {rotulo}
          </label>
        ))}
      </div>
      {erro && (
        <p className="erro-campo" id={idErro}>
          {erro}
        </p>
      )}
      {valor.localizacao === 'com um setor' && (
        <div className="campo">
          <label htmlFor={`${id}-setor`}>Qual setor?</label>
          <input
            id={`${id}-setor`}
            type="text"
            list={`${id}-sugestoes`}
            value={valor.setor}
            aria-invalid={erroSetor ? true : undefined}
            aria-describedby={erroSetor ? `${id}-setor-erro` : undefined}
            onChange={(evento) => onMudar({ ...valor, setor: evento.target.value })}
          />
          <datalist id={`${id}-sugestoes`}>
            {SUGESTOES_DE_SETOR.map((setor) => (
              <option key={setor} value={setor} />
            ))}
          </datalist>
          {erroSetor && (
            <p className="erro-campo" id={`${id}-setor-erro`}>
              {erroSetor}
            </p>
          )}
        </div>
      )}
    </fieldset>
  )
}
