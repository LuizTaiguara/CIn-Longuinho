// Caminhos para mandar alguém ao login e trazer de volta.

// Só caminho relativo do próprio site. O resto vira a página inicial (a API faz a mesma conferência).
export function retornoSeguro(retorno) {
  if (typeof retorno !== 'string' || !retorno.startsWith('/') || retorno.startsWith('//') || retorno.includes('\\')) {
    return '/'
  }
  return retorno
}

// Tela /login do site, que explica o login antes de mandar ao Google.
export function telaDeLogin(retorno, erro) {
  const params = new URLSearchParams()
  if (erro) params.set('erro', erro)
  params.set('retorno', retornoSeguro(retorno))
  return `/login?${params}`
}
