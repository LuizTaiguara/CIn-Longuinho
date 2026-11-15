// Escolha de locais (US-06, US-15): caixas de marcar com o vocabulário de GET /api/locais, mais
// "Outro lugar" com texto livre. Dá para marcar vários. A lista não pode bloquear o cadastro
// (US-06, casos de falha): se ela não carregar, sobra o campo livre.
//
// Valor: { selecionados: string[], temOutro: boolean, outro: string }

export const LOCAIS_VAZIOS = Object.freeze({ selecionados: [], temOutro: false, outro: '' })

// Valor inicial a partir dos locais de um item (para corrigir). Local fora da lista vira uma
// caixa marcada a mais, para não sumir da tela.
export function valorDosLocais(locais) {
  return { ...LOCAIS_VAZIOS, selecionados: [...locais] }
}

// Lista final de locais, sem repetição. "Outro lugar" aceita vários separados por vírgula.
export function locaisEscolhidos(valor) {
  const outros = valor.temOutro ? valor.outro.split(',').map((l) => l.trim()).filter(Boolean) : []
  return [...new Set([...valor.selecionados, ...outros])]
}

export default function CampoLocais({ id, legenda, locais, valor, onMudar, erro }) {
  const conhecidos = locais.lista.map((l) => l.nome)
  const opcoes = [...conhecidos, ...valor.selecionados.filter((nome) => !conhecidos.includes(nome))]
  const idErro = `${id}-erro`

  const alternar = (nome) => {
    const selecionados = valor.selecionados.includes(nome)
      ? valor.selecionados.filter((n) => n !== nome)
      : [...valor.selecionados, nome]
    onMudar({ ...valor, selecionados })
  }

  return (
    <fieldset className="campo-grupo" aria-describedby={erro ? idErro : undefined} aria-invalid={erro ? true : undefined}>
      <legend>{legenda}</legend>
      {locais.carregando && <p className="aviso">Carregando os locais…</p>}
      {locais.erro && <p className="aviso">A lista de locais não carregou. Use "Outro lugar".</p>}
      <div className="opcoes">
        {opcoes.map((nome, n) => (
          <label key={nome} className="opcao">
            <input
              type="checkbox"
              id={n === 0 ? id : undefined}
              checked={valor.selecionados.includes(nome)}
              onChange={() => alternar(nome)}
            />
            {nome}
          </label>
        ))}
        <label className="opcao">
          <input
            type="checkbox"
            id={opcoes.length === 0 ? id : undefined}
            checked={valor.temOutro}
            onChange={() => onMudar({ ...valor, temOutro: !valor.temOutro })}
          />
          Outro lugar
        </label>
      </div>
      {valor.temOutro && (
        <div className="campo">
          <label htmlFor={`${id}-outro`}>Qual? (se forem vários, separe por vírgula)</label>
          <input
            id={`${id}-outro`}
            type="text"
            value={valor.outro}
            onChange={(evento) => onMudar({ ...valor, outro: evento.target.value })}
          />
        </div>
      )}
      {erro && (
        <p className="erro-campo" id={idErro}>
          {erro}
        </p>
      )}
    </fieldset>
  )
}
