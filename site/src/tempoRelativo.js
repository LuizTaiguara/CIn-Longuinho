// "Há quanto tempo", em português (SCRUM-99, US-04).
// "Reivindicado há 2 horas" e "reivindicado há 3 semanas" dizem coisas diferentes: a segunda
// convida quem procura a ir conferir se o objeto ainda está lá. Por isso o tempo aparece sempre.

const MINUTO = 60 * 1000
const HORA = 60 * MINUTO
const DIA = 24 * HORA
const SEMANA = 7 * DIA
const MES = 30 * DIA
const ANO = 365 * DIA

const plural = (n, singular, varios) => `há ${n} ${n === 1 ? singular : varios}`

// `data`: texto ISO 8601 (como vem da API) ou Date. `agora`: para testar; padrão é o relógio.
function lerData(data) {
  if (data === null || data === undefined || data === '') return null
  const quando = new Date(data)
  return Number.isNaN(quando.getTime()) ? null : quando
}

export function tempoRelativo(data, agora = new Date()) {
  const quando = lerData(data)
  if (!quando) return ''
  const passado = new Date(agora).getTime() - quando.getTime()

  // Relógio da máquina um pouco adiantado ou atrasado não vira "daqui a 2 minutos".
  if (passado < MINUTO) return 'agora há pouco'
  if (passado < HORA) return plural(Math.floor(passado / MINUTO), 'minuto', 'minutos')
  if (passado < DIA) return plural(Math.floor(passado / HORA), 'hora', 'horas')
  if (passado < 2 * DIA) return 'ontem'
  if (passado < SEMANA) return plural(Math.floor(passado / DIA), 'dia', 'dias')
  if (passado < MES) return plural(Math.floor(passado / SEMANA), 'semana', 'semanas')
  if (passado < ANO) return plural(Math.floor(passado / MES), 'mês', 'meses')
  return plural(Math.floor(passado / ANO), 'ano', 'anos')
}

// Data completa para o `title` (passar o mouse) e para quem precisa da data exata.
// Fuso do Recife: é onde o CIn fica, e assim a data não muda conforme a máquina de quem lê.
const FORMATO_COMPLETO = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'long',
  timeStyle: 'short',
  timeZone: 'America/Recife',
})

export function dataCompleta(data) {
  const quando = lerData(data)
  if (!quando) return ''
  return FORMATO_COMPLETO.format(quando)
}
