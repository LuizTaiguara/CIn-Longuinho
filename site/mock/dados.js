// Dados FICTÍCIOS para o mock local. Nenhum é anúncio real, e não há e-mail de ninguém aqui.
// Os nomes de local são os do levantamento do F-07 (SCRUM-64, docs/espaco-fisico/).
// O formato segue ItemResumo do contrato (shared/openapi.yaml, PR #8).

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

function item(id, tipo, descricao, local, situacao, data, extras = {}) {
  return {
    id: `item_${id}`,
    tipo,
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
    ...extras,
  }
}

export const itens = [
  item('0012', 'achado', 'Garrafa térmica azul com adesivo do CIn', ['Grad 5'], 'aberto', '2026-11-12T14:32:00Z'),
  item('0011', 'perdido', 'Carregador de notebook USB-C, cabo branco', ['Grad 3', 'Laboratório de hardware'], 'aberto', '2026-11-11T10:05:00Z', { localizacao: null }),
  item('0010', 'achado', 'Molho de chaves com chaveiro de pinguim', ['Anfiteatro'], 'reivindicado', '2026-11-08T17:20:00Z', { data_situacao: '2026-11-09T09:00:00Z' }),
  item('0009', 'achado', 'Óculos de grau com armação preta', ['Grad 1'], 'encerrado', '2026-11-05T11:40:00Z', {
    localizacao: 'devolvido',
    fonte_encerramento: 'terceiro',
    data_situacao: '2026-11-06T15:10:00Z',
  }),
  item('0008', 'perdido', 'Fone de ouvido sem fio preto, estojo redondo', ['Grad 2'], 'aberto', '2026-11-04T08:55:00Z'),
  item('0007', 'achado', 'Calculadora científica Casio', ['Laboratório de pós-graduação'], 'aberto', '2026-11-01T16:00:00Z', {
    localizacao: 'com um setor',
    setor: 'Secretaria da graduação',
  }),
  item('0006', 'perdido', 'Caderno espiral verde de Cálculo', ['Grad 4'], 'encerrado', '2026-10-29T13:15:00Z', {
    fonte_encerramento: 'confirmação do autor',
    data_situacao: '2026-10-30T10:00:00Z',
  }),
  item('0005', 'achado', 'Mouse sem fio cinza', ['Grad 5', 'Grad 4'], 'aberto', '2026-10-27T09:30:00Z'),
]
