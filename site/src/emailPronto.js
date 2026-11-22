// Links do e-mail pronto (US-07, ADR-011). O site não envia nada: abre o e-mail já escrito no
// programa da pessoa (ou no Gmail, já que toda conta do CIn é Google), e ela envia da própria
// conta. Se nada abrir, o texto fica na tela para copiar.

const codificar = encodeURIComponent

// No mailto, quebra de linha é CRLF (RFC 6068).
export function linkMailto({ para, assunto, corpo }) {
  return `mailto:${para}?subject=${codificar(assunto)}&body=${codificar(corpo.replace(/\r?\n/g, '\r\n'))}`
}

export function linkGmail({ para, assunto, corpo }) {
  return `https://mail.google.com/mail/?view=cm&to=${codificar(para)}&su=${codificar(assunto)}&body=${codificar(corpo)}`
}

export function textoParaCopiar({ para, assunto, corpo }) {
  return `Para: ${para}\nAssunto: ${assunto}\n\n${corpo}`
}
