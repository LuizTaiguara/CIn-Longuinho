// Dados FICTÍCIOS para o mock local. Nenhum é anúncio real, e não há e-mail de ninguém aqui.
// Os nomes de local são os do levantamento do F-07 (SCRUM-64, docs/espaco-fisico/).
// O formato segue o contrato (shared/openapi.yaml): todos os campos sempre presentes, `null` quando vazio.
//
// Campos que começam com `_` são internos do mock (autoria, texto original, ocultação, retenção)
// e NUNCA saem nas respostas: o servidor do mock os tira antes de responder, como a API faria.
// A autoria é só `_autor: 'voce'` (a conta do login simulado) ou `'outra'`. Não há endereço.

export const locais = [
  { nome: 'Grad 1', bloco: 'Vermelho' },
  { nome: 'Grad 2', bloco: 'Vermelho' },
  { nome: 'Grad 3', bloco: 'Vermelho' },
  { nome: 'Grad 4', bloco: 'Vermelho' },
  { nome: 'Grad 5', bloco: 'Vermelho' },
  { nome: 'Laboratório de hardware', bloco: 'Vermelho' },
  { nome: 'Laboratório de pós-graduação', bloco: 'Vermelho' },
  { nome: 'Anfiteatro', bloco: 'Vermelho' },
]

// Nome devolvido por GET /eu no login simulado. Fictício.
export const NOME_DA_SESSAO = 'Pessoa Fictícia'

function item(id, tipo, descricao, local, situacao, data, extras = {}) {
  return {
    id: `item_${id}`,
    tipo,
    revisar: false,
    descricao,
    local,
    situacao,
    localizacao: tipo === 'achado' ? 'com quem achou' : null,
    setor: null,
    foto_url: null,
    data_registro: data,
    data_atualizacao: null,
    fonte_encerramento: null,
    data_situacao: data,
    origem: 'lista',
    codigo: null,
    foi_para_a_lista: true,
    _autor: 'outra',
    _oculto: false,
    _texto: `Oi, pessoal! ${descricao}. Quem souber, me responde aqui. Contato: [TELEFONE MASCARADO]`,
    ...extras,
  }
}

// Devolve uma cópia nova a cada chamada: o mock muda os dados em memória (PATCH, encerrar, ocultar…),
// e os testes precisam começar sempre do mesmo ponto.
export function criarItens() {
  return [
    item('0012', 'achado', 'Garrafa térmica azul com adesivo do CIn', ['Grad 5'], 'aberto', '2026-11-12T14:32:00Z', {
      _autor: 'voce',
    }),
    item('0011', 'perdido', 'Carregador de notebook USB-C, cabo branco', ['Grad 3', 'Laboratório de hardware'], 'aberto', '2026-11-11T10:05:00Z'),
    item('0010', 'achado', 'Molho de chaves com chaveiro de pinguim', ['Anfiteatro'], 'reivindicado', '2026-11-08T17:20:00Z', {
      data_situacao: '2026-11-09T09:00:00Z',
      revisar: true,
    }),
    item('0009', 'achado', 'Óculos de grau com armação preta', ['Grad 1'], 'encerrado', '2026-11-05T11:40:00Z', {
      localizacao: 'devolvido',
      fonte_encerramento: 'terceiro',
      data_situacao: '2026-11-06T15:10:00Z',
    }),
    item('0008', 'perdido', 'Fone de ouvido sem fio preto, estojo redondo', ['Grad 2'], 'aberto', '2026-11-04T08:55:00Z', {
      _autor: 'voce',
      origem: 'site',
      codigo: 'AP-K7F3Q2',
      foi_para_a_lista: false,
      _texto: null,
    }),
    item('0007', 'achado', 'Calculadora científica Casio', ['Laboratório de pós-graduação'], 'aberto', '2026-11-01T16:00:00Z', {
      localizacao: 'com um setor',
      setor: 'SecGrad',
    }),
    item('0006', 'perdido', 'Caderno espiral verde de Cálculo', ['Grad 4'], 'encerrado', '2026-10-29T13:15:00Z', {
      fonte_encerramento: 'confirmação do autor',
      data_situacao: '2026-10-30T10:00:00Z',
    }),
    item('0005', 'achado', 'Mouse sem fio cinza', ['Grad 5', 'Grad 4'], 'aberto', '2026-10-27T09:30:00Z', {
      localizacao: 'caixa do bloco A/E',
    }),
    // Oculto pela própria autora: some do catálogo e aparece só em "Meus anúncios", marcado.
    item('0004', 'achado', 'Estojo rosa com canetas', ['Grad 1'], 'aberto', '2026-10-20T12:00:00Z', {
      _autor: 'voce',
      _oculto: true,
    }),
    // Oculto por outra pessoa: não aparece em lugar nenhum para a sessão simulada.
    item('0003', 'perdido', 'Crachá de visitante', ['Anfiteatro'], 'aberto', '2026-10-18T12:00:00Z', {
      _oculto: true,
    }),
  ]
}

// Mensagens retidas em quarentena (US-02). Só a que abriu uma thread da própria sessão aparece,
// e só em GET /eu/itens (exceção da invariante 5).
export function criarRetidas() {
  return [
    {
      id: 'retida_3',
      descricao: 'Alguém viu um guarda-chuva preto? Ficou ontem perto da cantina',
      motivo_retencao: 'direcao_ambigua',
      data_registro: '2026-11-13T19:45:00Z',
      _autor: 'voce',
      _classificada: false,
    },
    {
      id: 'retida_2',
      descricao: 'Mensagem retida de outra pessoa',
      motivo_retencao: 'confianca_baixa',
      data_registro: '2026-11-10T08:00:00Z',
      _autor: 'outra',
      _classificada: false,
    },
  ]
}
