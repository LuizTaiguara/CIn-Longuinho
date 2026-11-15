"""US-15, último critério: um único aviso por thread ao autor do anúncio, com o link do item.

Quem recebe: item `origem = 'lista'`, não oculto, não encerrado, com `autor_email`, sem
`aviso_autor_enviado_em`, que o autor não classificou ele mesmo em "Meus anúncios" (esse já está
no site), e com `data_anuncio` a partir de `WORKER_AVISO_A_PARTIR_DE`.

Essa data existe porque a primeira leitura do Gmail traz o histórico inteiro da conta: sem ela, o
worker avisaria de uma vez os autores de anúncios antigos. **Sem a variável, nenhum aviso sai.**
Em produção, ponha a data em que o worker passou a ler a lista.

Ordem das operações, para nunca avisar duas vezes: na mesma transação, reserva o aviso
(`UPDATE ... WHERE aviso_autor_enviado_em IS NULL`), grava o evento, envia e só então faz commit.
Se o envio falha, a transação volta e o aviso fica para o próximo ciclo.
"""
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Mapping, Optional

from worker.envio import EmailSaida

log = logging.getLogger("worker.aviso")

ASSUNTO = "Seu anúncio está no catálogo de Achados e Perdidos do CIn"

CORPO = """Olá!

O que você mandou para a lista achados-perdidos@cin.ufpe.br já está no catálogo:
{link}

Para corrigir o anúncio ou encerrá-lo quando o objeto voltar para o dono, basta entrar no site com a sua conta do CIn. Não precisa responder a este e-mail.

Este é o único aviso sobre esta conversa.

Achados e Perdidos do CIn (mensagem automática)
"""


@dataclass(frozen=True)
class ConfigAviso:
    site_url: str
    a_partir_de: Optional[datetime]

    @staticmethod
    def do_ambiente(ambiente: Optional[Mapping[str, str]] = None) -> "ConfigAviso":
        env = os.environ if ambiente is None else ambiente
        bruto = (env.get("WORKER_AVISO_A_PARTIR_DE") or "").strip()
        a_partir_de = None
        if bruto:
            try:
                a_partir_de = datetime.combine(date.fromisoformat(bruto), time.min, tzinfo=timezone.utc)
            except ValueError as erro:
                raise ValueError(f"WORKER_AVISO_A_PARTIR_DE inválida: {bruto!r}. Use AAAA-MM-DD.") from erro
        return ConfigAviso(site_url=(env.get("SITE_URL") or "").strip().rstrip("/"), a_partir_de=a_partir_de)

    def motivo_desligado(self) -> Optional[str]:
        if self.a_partir_de is None:
            return "WORKER_AVISO_A_PARTIR_DE não definida"
        if not self.site_url:
            return "SITE_URL não definida"
        return None


def link_do_item(site_url: str, item_id: int) -> str:
    """Mesmo formato de id da API: `item_<id>` (shared/AGENTS.md)."""
    return f"{site_url}/itens/item_{item_id}"


def montar_aviso(autor_email: str, item_id: int, site_url: str) -> EmailSaida:
    return EmailSaida(para=autor_email, assunto=ASSUNTO, corpo=CORPO.format(link=link_do_item(site_url, item_id)))
