// Estado dos filtros do catálogo (SCRUM-98).
// Os filtros vivem na URL (?texto=…&local=…), para que uma busca possa ser compartilhada
// e sobreviva ao recarregar a página. Nomes iguais aos parâmetros de GET /api/itens.
//
// O cliente NÃO normaliza acento nem maiúscula: isso é do servidor (SCRUM-96).

export const FILTROS_VAZIOS = Object.freeze({ texto: '', local: '', tipo: '', situacao: '' })

const CAMPOS = Object.keys(FILTROS_VAZIOS)

export const TIPOS = ['achado', 'perdido']
export const SITUACOES = ['aberto', 'reivindicado', 'encerrado']

export function filtrosDaUrl(search) {
  const params = new URLSearchParams(search)
  const filtros = { ...FILTROS_VAZIOS }
  for (const campo of CAMPOS) filtros[campo] = (params.get(campo) ?? '').trim()
  // Valor fora do vocabulário fechado vira "sem filtro", em vez de um 400 da API.
  if (!TIPOS.includes(filtros.tipo)) filtros.tipo = ''
  if (!SITUACOES.includes(filtros.situacao)) filtros.situacao = ''
  return filtros
}

// Só os filtros preenchidos entram na query; serve tanto para a URL da página quanto para a API.
export function paramsDosFiltros(filtros) {
  const params = new URLSearchParams()
  for (const campo of CAMPOS) {
    const valor = (filtros[campo] ?? '').trim()
    if (valor) params.set(campo, valor)
  }
  return params
}

export function temFiltroAtivo(filtros) {
  return CAMPOS.some((campo) => (filtros[campo] ?? '').trim() !== '')
}
