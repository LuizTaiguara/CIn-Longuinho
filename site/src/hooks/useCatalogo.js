import { useCallback, useEffect, useState } from 'react'
import { listarItens, listarLocais } from '../api/cliente.js'

// Busca os itens sempre que os filtros mudam. Uma busca nova cancela a anterior,
// para uma resposta atrasada não sobrescrever a mais recente.
// `tentarDeNovo` refaz a mesma busca (botão da tela de erro, SCRUM-100).
export function useItens(filtros) {
  const [estado, setEstado] = useState({ carregando: true, erro: null, resposta: null })
  const [tentativa, setTentativa] = useState(0)
  const chave = JSON.stringify(filtros)

  useEffect(() => {
    const controle = new AbortController()
    setEstado((anterior) => ({ ...anterior, carregando: true, erro: null }))
    listarItens(JSON.parse(chave), { signal: controle.signal })
      .then((resposta) => setEstado({ carregando: false, erro: null, resposta }))
      .catch((erro) => {
        if (erro.name === 'AbortError') return
        // Sem resposta antiga na tela: depois de uma falha, nada de mostrar lista desatualizada.
        setEstado({ carregando: false, erro, resposta: null })
      })
    return () => controle.abort()
  }, [chave, tentativa])

  const tentarDeNovo = useCallback(() => setTentativa((n) => n + 1), [])
  return { ...estado, tentarDeNovo }
}

// Lista de locais para o filtro. Se falhar, o catálogo continua funcionando sem o filtro de local.
export function useLocais() {
  const [estado, setEstado] = useState({ carregando: true, erro: null, lista: [] })

  useEffect(() => {
    const controle = new AbortController()
    listarLocais({ signal: controle.signal })
      .then((lista) => setEstado({ carregando: false, erro: null, lista: Array.isArray(lista) ? lista : [] }))
      .catch((erro) => {
        if (erro.name === 'AbortError') return
        setEstado({ carregando: false, erro, lista: [] })
      })
    return () => controle.abort()
  }, [])

  return estado
}
