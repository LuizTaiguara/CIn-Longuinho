import { useEffect, useState } from 'react'
import { listarItens, listarLocais } from '../api/cliente.js'

// Busca os itens sempre que os filtros mudam. Uma busca nova cancela a anterior,
// para uma resposta atrasada não sobrescrever a mais recente.
export function useItens(filtros) {
  const [estado, setEstado] = useState({ carregando: true, erro: null, resposta: null })
  const chave = JSON.stringify(filtros)

  useEffect(() => {
    const controle = new AbortController()
    setEstado((anterior) => ({ ...anterior, carregando: true, erro: null }))
    listarItens(JSON.parse(chave), { signal: controle.signal })
      .then((resposta) => setEstado({ carregando: false, erro: null, resposta }))
      .catch((erro) => {
        if (erro.name === 'AbortError') return
        setEstado({ carregando: false, erro, resposta: null })
      })
    return () => controle.abort()
  }, [chave])

  return estado
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
