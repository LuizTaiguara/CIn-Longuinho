import { useCallback, useEffect, useState } from 'react'
import { filtrosDaUrl, paramsDosFiltros } from '../filtros.js'

// Mantém os filtros na URL: dá para compartilhar uma busca, e o "voltar" do navegador desfaz o filtro.
export function useFiltrosNaUrl() {
  const [filtros, setFiltros] = useState(() => filtrosDaUrl(window.location.search))

  useEffect(() => {
    const aoVoltar = () => setFiltros(filtrosDaUrl(window.location.search))
    window.addEventListener('popstate', aoVoltar)
    return () => window.removeEventListener('popstate', aoVoltar)
  }, [])

  const mudarFiltros = useCallback((novos) => {
    const query = paramsDosFiltros(novos).toString()
    const url = `${window.location.pathname}${query ? `?${query}` : ''}`
    window.history.pushState(null, '', url)
    setFiltros(filtrosDaUrl(query))
  }, [])

  return [filtros, mudarFiltros]
}
