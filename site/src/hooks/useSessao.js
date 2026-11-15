// Sessão da conta do CIn (US-15). Uma consulta a GET /api/eu quando o site abre, compartilhada
// por todas as telas. 401 é "ninguém entrou", não erro: o catálogo é aberto para leitura.
// Se a API ou o login estiverem fora, o site segue como anônimo (US-15, casos de falha).

import { createContext, createElement, useCallback, useContext, useEffect, useState } from 'react'
import { obterSessao } from '../api/cliente.js'

const ANONIMO = { carregando: false, autenticado: false, nome: null }
const ContextoSessao = createContext({ ...ANONIMO, recarregar: () => {} })

export function ProvedorSessao({ children }) {
  const [estado, setEstado] = useState({ carregando: true, autenticado: false, nome: null })
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    const controle = new AbortController()
    obterSessao({ signal: controle.signal })
      .then((dados) =>
        setEstado(dados?.autenticado ? { carregando: false, autenticado: true, nome: dados.nome ?? null } : ANONIMO),
      )
      .catch((erro) => {
        if (erro.name === 'AbortError') return
        setEstado(ANONIMO)
      })
    return () => controle.abort()
  }, [versao])

  const recarregar = useCallback(() => setVersao((n) => n + 1), [])

  return createElement(ContextoSessao.Provider, { value: { ...estado, recarregar } }, children)
}

export function useSessao() {
  return useContext(ContextoSessao)
}
