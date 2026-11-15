// Selo "revisar" (US-04, ADR-004): o classificador publicou o anúncio, mas com confiança média.
// O item aparece normalmente; o selo só avisa para conferir antes de confiar no tipo.

const EXPLICACAO = 'A classificação automática deste anúncio teve confiança média: confira o texto antes de confiar nela.'

export default function SeloRevisar() {
  return (
    <span className="selo-revisar" title={EXPLICACAO}>
      revisar<span className="visualmente-oculto"> ({EXPLICACAO})</span>
    </span>
  )
}
