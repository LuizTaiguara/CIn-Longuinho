// Mock LOCAL e TEMPORÁRIO da API, só para o `npm run dev` funcionar sem backend.
// O mock oficial da SCRUM-67 foi dispensado: a API de verdade (FastAPI, `api/`) substitui.
// Com ela de pé, rode `API_URL=http://localhost:8000 npm run dev` e este mock sai de cena.
//
// Este arquivo só faz a parte HTTP (ler corpo, cookie, multipart). As regras estão em `rotas.js`.
//
// Variáveis para ver estados no navegador:
//   MOCK_VAZIO=1           catálogo sem nenhum item (primeira execução)
//   MOCK_FALHA=1           API fora do ar (banco indisponível): tudo responde 503
//   MOCK_CONTATO_FALHA=1   o contato com quem anunciou responde 502 (envio falhou)
//   MOCK_LOGIN_FORA=1      o login volta como conta de fora do CIn
//
// Login simulado: "Entrar com a conta do CIn" grava o cookie `sessao_mock` e volta ao `retorno`.

import { COOKIE_DA_SESSAO, criarMock } from './rotas.js'

export { filtrarItens, paginar } from './rotas.js'

function lerCorpo(req) {
  return new Promise((resolver, rejeitar) => {
    const partes = []
    req.on('data', (parte) => partes.push(parte))
    req.on('end', () => resolver(Buffer.concat(partes)))
    req.on('error', rejeitar)
  })
}

export function temSessao(cabecalhoCookie) {
  return String(cabecalhoCookie ?? '')
    .split(';')
    .some((par) => par.trim() === `${COOKIE_DA_SESSAO}=1`)
}

// Lê o campo `foto` de um multipart/form-data. Basta para o mock: um campo, um arquivo.
export function lerFotoDoMultipart(corpo, tipoDoConteudo) {
  const limite = /boundary=(?:"([^"]+)"|([^;]+))/.exec(tipoDoConteudo ?? '')
  if (!limite) return null
  const separador = Buffer.from(`--${limite[1] ?? limite[2]}`)
  let inicio = corpo.indexOf(separador)
  while (inicio !== -1) {
    const fim = corpo.indexOf(separador, inicio + separador.length)
    if (fim === -1) break
    const parte = corpo.subarray(inicio + separador.length, fim)
    const fimDoCabecalho = parte.indexOf('\r\n\r\n')
    if (fimDoCabecalho !== -1) {
      const cabecalho = parte.subarray(0, fimDoCabecalho).toString('utf8')
      if (/name="foto"/.test(cabecalho)) {
        const tipo = /content-type:\s*([^\r\n]+)/i.exec(cabecalho)?.[1]?.trim() ?? ''
        // Tira o \r\n antes do próximo separador.
        const dados = parte.subarray(fimDoCabecalho + 4, parte.length - 2)
        return { tipo, tamanho: dados.length, dados }
      }
    }
    inicio = fim
  }
  return null
}

export function mockLocal() {
  const mock = criarMock({
    vazio: Boolean(process.env.MOCK_VAZIO),
    falha: Boolean(process.env.MOCK_FALHA),
    contatoFalha: Boolean(process.env.MOCK_CONTATO_FALHA),
    loginFora: Boolean(process.env.MOCK_LOGIN_FORA),
  })

  return {
    name: 'mock-local-api',
    configureServer(server) {
      server.middlewares.use('/api', async (req, res) => {
        const url = new URL(req.url, 'http://local')
        const tipoDoConteudo = req.headers['content-type'] ?? ''
        const bruto = ['POST', 'PATCH'].includes(req.method) ? await lerCorpo(req) : Buffer.alloc(0)

        let corpo = null
        let foto = null
        if (tipoDoConteudo.startsWith('multipart/form-data')) {
          foto = lerFotoDoMultipart(bruto, tipoDoConteudo)
        } else if (bruto.length) {
          try {
            corpo = JSON.parse(bruto.toString('utf8'))
          } catch {
            corpo = null
          }
        }

        const resposta = mock.tratar({
          metodo: req.method,
          caminho: url.pathname,
          query: url.searchParams,
          sessao: temSessao(req.headers.cookie),
          corpo,
          foto,
        })

        res.statusCode = resposta.status
        for (const [nome, valor] of Object.entries(resposta.cabecalhos ?? {})) res.setHeader(nome, valor)
        if (resposta.binario) return res.end(resposta.binario)
        if (resposta.corpo === null || resposta.corpo === undefined) return res.end()
        res.setHeader('Content-Type', 'application/json; charset=utf-8')
        res.end(JSON.stringify(resposta.corpo))
      })
    },
  }
}
