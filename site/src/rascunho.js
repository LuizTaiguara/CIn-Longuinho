// Rascunho guardado no navegador quando a sessão expira no meio de uma edição (US-15, casos de
// falha): a pessoa volta do login para o mesmo item sem perder o que digitou.
// Guarda só o que a própria pessoa escreveu no formulário. Nunca e-mail, nunca nada da API.
// Se o navegador não deixar guardar (modo privado, cota), segue sem rascunho.

const PREFIXO = 'longuinho:rascunho:'

export function guardarRascunho(chave, dados) {
  try {
    window.localStorage.setItem(PREFIXO + chave, JSON.stringify(dados))
  } catch {
    // sem armazenamento: o rascunho se perde, mas a tela não quebra
  }
}

export function lerRascunho(chave) {
  try {
    const texto = window.localStorage.getItem(PREFIXO + chave)
    return texto ? JSON.parse(texto) : null
  } catch {
    return null
  }
}

export function apagarRascunho(chave) {
  try {
    window.localStorage.removeItem(PREFIXO + chave)
  } catch {
    // nada a fazer
  }
}
