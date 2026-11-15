// Rodapé com o canal humano de remoção (US-09, ADR-011). Quem aparece num anúncio que não
// publicou escreve para o endereço +remocao da conta do projeto; alguém do grupo oculta à mão.
// Não há automação nem formulário. O endereço vem de VITE_EMAIL_REMOCAO (.env.example).

import { useLocation } from 'react-router-dom'

const ENDERECO_PADRAO = 'remocao@exemplo.invalid'

export function enderecoDeRemocao() {
  const configurado = String(import.meta.env.VITE_EMAIL_REMOCAO ?? '').trim()
  return configurado || ENDERECO_PADRAO
}

// Na página de um item, o e-mail já sai com o link dele no assunto e no corpo, para o pedido
// identificar o item (US-09). Em outras páginas, vai sem item.
export function linkDeRemocao(endereco, caminho, origem = window.location.origin) {
  const item = /^\/itens\/([^/]+)$/.exec(caminho)
  if (!item) return `mailto:${endereco}?subject=${encodeURIComponent('Pedido de remoção de anúncio')}`
  const link = `${origem}${caminho}`
  const assunto = `Pedido de remoção do anúncio ${decodeURIComponent(item[1])}`
  const corpo = `Peço que este anúncio saia do catálogo: ${link}\n\nMotivo: `
  return `mailto:${endereco}?subject=${encodeURIComponent(assunto)}&body=${encodeURIComponent(corpo)}`
}

export default function Rodape() {
  const { pathname } = useLocation()
  const endereco = enderecoDeRemocao()

  return (
    <footer className="rodape">
      <p>
        Apareceu num anúncio que não é seu e quer que ele saia do catálogo? Escreva para{' '}
        <a href={linkDeRemocao(endereco, pathname)}>{endereco}</a>.
      </p>
    </footer>
  )
}
