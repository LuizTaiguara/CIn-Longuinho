import { useCallback, useEffect, useState } from 'react'
import { obterItem } from '../api/cliente.js'

// Carrega um item (GET /api/itens/{id}). `naoEncontrado` cobre oculto, retido e inexistente,
// sem distinguir (a API devolve o mesmo 404). `trocarItem` atualiza a tela depois de uma ação.
export function useItem(id) {
  const [estado, setEstado] = useState({ carregando: true, erro: null, item: null })
  const [tentativa, setTentativa] = useState(0)

  useEffect(() => {
    const controle = new AbortController()
    setEstado({ carregando: true, erro: null, item: null })
    obterItem(id, { signal: controle.signal })
      .then((item) => setEstado({ carregando: false, erro: null, item }))
      .catch((erro) => {
        if (erro.name === 'AbortError') return
        setEstado({ carregando: false, erro, item: null })
      })
    return () => controle.abort()
  }, [id, tentativa])

  const tentarDeNovo = useCallback(() => setTentativa((n) => n + 1), [])
  const trocarItem = useCallback((item) => setEstado({ carregando: false, erro: null, item }), [])

  return {
    ...estado,
    naoEncontrado: estado.erro?.status === 404,
    tentarDeNovo,
    trocarItem,
  }
}
