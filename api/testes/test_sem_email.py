"""US-05 / SCRUM-101: o e-mail do autor não é campo de resposta e não vai para o log."""

from __future__ import annotations

import logging

from api import privacidade
from api.testes.dados import AUTORA, OUTRA_PESSOA, criar_item, criar_mensagem


def test_item_publicado_nao_traz_o_endereco_do_autor_na_resposta_da_api(entrar, con):
    numero = criar_item(con, thread_id="thread-a", autor_email=AUTORA)
    criar_mensagem(con, "thread-a", remetente=f"Fic Teste <{AUTORA}>")

    for quem in (None, OUTRA_PESSOA, AUTORA):
        cliente = entrar(quem)
        for caminho in ("/api/itens", f"/api/itens/item_{numero}", "/api/itens?texto=garrafa"):
            resposta = cliente.get(caminho)
            assert resposta.status_code == 200
            assert AUTORA not in resposta.text, (quem, caminho)
            assert "autor_email" not in resposta.text
            assert "remetente" not in resposta.text


def test_endereco_dentro_da_descricao_sai_mascarado(cliente, con):
    criar_item(con, descricao=f"Carteira, falar com {AUTORA}", local=["Grad 5"], localizacao="com um setor", setor=f"SecGrad ({AUTORA})")

    item = cliente.get("/api/itens").json()["itens"][0]

    assert item["descricao"] == "Carteira, falar com [e-mail mascarado]"
    assert item["setor"] == "SecGrad ([e-mail mascarado])"


def test_busca_pelo_endereco_nao_encontra_o_item(entrar, con):
    criar_item(con, thread_id="thread-b", descricao=f"Carteira, falar com {AUTORA}")
    criar_mensagem(con, "thread-b", corpo=f"Achei uma carteira. Contato: {AUTORA}")

    for quem in (None, OUTRA_PESSOA):
        assert entrar(quem).get("/api/itens", params={"texto": AUTORA}).json()["itens"] == []
        assert entrar(quem).get("/api/itens", params={"texto": "fic.teste"}).json()["itens"] == []


def test_erro_de_parametro_nao_ecoa_o_valor_recebido(cliente, con):
    resposta = cliente.get("/api/itens", params={"tipo": AUTORA, "limite": AUTORA})
    assert resposta.status_code == 400
    assert AUTORA not in resposta.text


def test_log_de_acesso_mascara_endereco_na_query(cliente, con, caplog):
    caplog.set_level(logging.DEBUG)

    cliente.get("/api/itens", params={"texto": AUTORA})

    mensagens = [r.getMessage() for r in caplog.records if r.name == "api.acesso"]
    assert mensagens, "o acesso deveria ter sido registrado"
    assert AUTORA not in caplog.text
    assert "fic.teste%40" not in caplog.text
    assert any("[e-mail mascarado]" in m for m in mensagens)


def test_fabrica_de_logs_mascara_mensagem_argumentos_e_rastro(caplog):
    privacidade.instalar_mascara_de_logs()
    caplog.set_level(logging.DEBUG)
    log = logging.getLogger("teste.privacidade")

    log.info("autor %s", AUTORA)
    log.info("dicionario %(quem)s", {"quem": AUTORA})
    log.info(f"formatado {AUTORA}")
    try:
        raise ValueError(f"chave duplicada ({AUTORA})")
    except ValueError:
        log.exception("falhou")

    assert AUTORA not in caplog.text
    assert "[e-mail mascarado]" in caplog.text


def test_mascara_de_email_cobre_formatos_comuns():
    casos = {
        f"Fale com {AUTORA}.": "Fale com [e-mail mascarado]",
        f"<{AUTORA}>": "<[e-mail mascarado]>",
        f"mailto:{AUTORA}": "mailto:[e-mail mascarado]",
        "fulano@cin": "[e-mail mascarado]",
        f"({AUTORA})": "([e-mail mascarado])",
        "FIC.TESTE@CIN.UFPE.BR": "[e-mail mascarado]",
        "texto=fic.teste%40cin.ufpe.br&pagina=2": "texto=[e-mail mascarado]&pagina=2",
        "sem endereço aqui": "sem endereço aqui",
    }
    for entrada, esperado in casos.items():
        assert privacidade.mascarar_emails(entrada).rstrip(".") == esperado.rstrip("."), entrada
