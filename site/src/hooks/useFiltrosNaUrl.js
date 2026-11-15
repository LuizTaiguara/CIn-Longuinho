import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { filtrosDaUrl, paginaDaUrl, paramsDosFiltros } from '../filtros.js'

// Mantém filtros e página na URL: dá para compartilhar uma busca, e o "voltar" do navegador desfaz
// o filtro ou a troca de página. Mudar um filtro volta para a primeira página.
export function useFiltrosNaUrl() {
  const [params, setParams] = useSearchParams()
  const busca = params.toString()
  const filtros = useMemo(() => filtrosDaUrl(busca), [busca])
  const pagina = paginaDaUrl(busca)

  const mudarFiltros = useCallback((novos) => setParams(paramsDosFiltros(novos)), [setParams])

  const mudarPagina = useCallback(
    (novaPagina) => {
      const novos = paramsDosFiltros(filtros)
      if (novaPagina > 1) novos.set('pagina', String(novaPagina))
      setParams(novos)
    },
    [filtros, setParams],
  )

  return { filtros, pagina, mudarFiltros, mudarPagina }
}
