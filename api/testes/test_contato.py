"""US-05 (botão de contato) e SCRUM-102: falar com quem anunciou sem ver o endereço.

`POST /itens/{id}/contato` encaminha a mensagem pela conta do projeto, com o endereço da sessão
em `Reply-To`. SMTP nunca roda em teste (fixture `smtp_proibido`, no conftest); o envio real é
conferido com um SMTP falso no lugar de `smtplib.SMTP`.
"""

from __future__ import annotations

import email
import email.policy
import logging
import smtplib
from pathlib import Path

import pytest

from api import config as modulo_config
from api import envio
from api.main import criar_app
from api.testes.conftest import fazer_config
from api.testes.dados import AUTORA, OUTRA_PESSOA, criar_item

MENSAGEM = "Oi! Acho que essa garrafa é minha, tem um adesivo do CIn na tampa. Posso buscar amanhã?"
REMETENTE_PROJETO = "fic.projeto@cin.ufpe.br"


def _emails(pasta: Path) -> list[email.message.EmailMessage]:
    if not pasta.exists():
        return []
    return [
        email.message_from_bytes(arquivo.read_bytes(), policy=email.policy.default)
        for arquivo in sorted(pasta.glob("*.eml"))
    ]


def _eventos_de_contato(con, item_id: int) -> list[dict]:
    return con.execute(
        "SELECT fonte, aplicado, detalhes, situacao_anterior, situacao_nova FROM evento"
        " WHERE item_id = %s AND tipo_evento = 'contato'",
        [item_id],
    ).fetchall()


class EnvioFalso:
    def __init__(self, falhar: bool = False) -> None:
        self.falhar = falhar
        self.enviadas: list[envio.Mensagem] = []

    def enviar(self, mensagem: envio.Mensagem) -> None:
        if self.falhar:
            raise envio.FalhaEnvio("simulada")
        self.enviadas.append(mensagem)


@pytest.fixture
def no_arquivo(url_banco, con, tmp_path):
    """Cliente com EMAIL_MODO_ENVIO=arquivo, gravando em tmp_path/emails."""
    from fastapi.testclient import TestClient

    from api.testes.conftest import cookie_de

    config = fazer_config(
        url_banco,
        email_modo_envio="arquivo",
        email_arquivo_dir=str(tmp_path / "emails"),
        email_remetente=REMETENTE_PROJETO,
        fotos_dir=str(tmp_path / "fotos"),
    )
    with TestClient(criar_app(config)) as cliente:
        cliente.cookies.update(cookie_de(config, OUTRA_PESSOA, "Pessoa Fictícia"))
        yield cliente, tmp_path / "emails"


# ---------------------------------------------------------------------------
# Critério: "minha mensagem é encaminhada sem que eu veja o endereço de destino"
# ---------------------------------------------------------------------------


def test_contato_encaminha_a_mensagem_sem_mostrar_o_endereco_de_destino(no_arquivo, con):
    cliente, pasta = no_arquivo
    item = criar_item(con, autor_email=AUTORA, descricao="Garrafa térmica azul com adesivo do CIn")

    resposta = cliente.post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM})

    assert resposta.status_code == 202
    assert resposta.content == b""
    for texto in [resposta.text, *(f"{n}: {v}" for n, v in resposta.headers.items())]:
        assert AUTORA not in texto.lower()
        assert "fic.teste" not in texto.lower()


def test_modo_arquivo_grava_o_eml_com_remetente_destinatario_e_reply_to_certos(no_arquivo, con):
    cliente, pasta = no_arquivo
    item = criar_item(con, autor_email=AUTORA, descricao="Garrafa térmica azul com adesivo do CIn")

    assert cliente.post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM}).status_code == 202

    [gravado] = _emails(pasta)
    assert gravado["From"] == REMETENTE_PROJETO
    assert gravado["To"] == AUTORA
    assert gravado["Reply-To"] == OUTRA_PESSOA
    assert gravado["Subject"] == "[Achados e Perdidos] Sobre o seu anúncio: Garrafa térmica azul com adesivo do CIn"
    corpo = gravado.get_content()
    assert MENSAGEM in corpo
    assert f"http://localhost:5173/itens/item_{item}" in corpo
    assert "Pessoa Fictícia" in corpo
    # O corpo não traz endereço de ninguém: o de quem escreveu vai só no Reply-To.
    assert AUTORA not in corpo and OUTRA_PESSOA not in corpo
    assert "achados-perdidos@cin.ufpe.br" not in gravado["To"]  # nunca posta na lista


def test_assunto_usa_a_descricao_curta_e_mascarada(no_arquivo, con):
    cliente, pasta = no_arquivo
    descricao = (
        "Casaco preto de moletom com capuz e zíper quebrado, ligar 81 99999-0000, "
        "deixei na cadeira do fundo do anfiteatro"
    )
    item = criar_item(con, autor_email=AUTORA, descricao=descricao)

    assert cliente.post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM}).status_code == 202

    [gravado] = _emails(pasta)
    assunto = gravado["Subject"]
    assert assunto.startswith("[Achados e Perdidos] Sobre o seu anúncio: Casaco preto")
    assert assunto.endswith("…")
    assert "99999" not in gravado.get_content()


def test_contato_registra_evento_sem_nenhum_endereco(no_arquivo, con):
    cliente, _ = no_arquivo
    item = criar_item(con, autor_email=AUTORA)

    cliente.post(f"/api/itens/item_{item}/contato", json={"mensagem": f"  {MENSAGEM}  "})

    [evento] = _eventos_de_contato(con, item)
    assert evento["fonte"] == "terceiro"
    assert evento["aplicado"] is True
    assert evento["detalhes"] == {"tamanho": len(MENSAGEM)}
    assert evento["situacao_anterior"] is None and evento["situacao_nova"] is None
    situacao = con.execute("SELECT situacao::text FROM item WHERE id = %s", [item]).fetchone()
    assert situacao["situacao"] == "aberto"  # contato não muda a situação


def test_contato_nao_escreve_endereco_nem_mensagem_no_log(no_arquivo, con, caplog):
    caplog.set_level(logging.DEBUG)
    cliente, _ = no_arquivo
    item = criar_item(con, autor_email=AUTORA)

    cliente.post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM})

    for registro in caplog.records:
        texto = registro.getMessage().lower()
        assert AUTORA not in texto and "fic.teste" not in texto
        assert OUTRA_PESSOA not in texto and "fic.outra" not in texto
        assert "adesivo" not in texto


def test_contato_com_item_encerrado_ainda_e_aceito(no_arquivo, con):
    cliente, pasta = no_arquivo
    item = criar_item(con, autor_email=AUTORA, situacao="encerrado", fonte_encerramento="terceiro")

    assert cliente.post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM}).status_code == 202
    assert len(_emails(pasta)) == 1


# ---------------------------------------------------------------------------
# Sessão, item e mensagem
# ---------------------------------------------------------------------------


def test_contato_sem_sessao_responde_401_e_nao_envia(cliente, entrar, con):
    falso = EnvioFalso()
    cliente.app.state.envio = falso
    item = criar_item(con)

    resposta = entrar(None).post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM})

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "NAO_AUTENTICADO"
    assert falso.enviadas == []
    assert _eventos_de_contato(con, item) == []


@pytest.mark.parametrize("caso", ["oculto", "inexistente", "id_invalido", "retida"])
def test_contato_com_item_nao_visivel_responde_404(cliente, entrar, con, caso):
    falso = EnvioFalso()
    cliente.app.state.envio = falso
    oculto = criar_item(con, oculto=True)
    id_ = {"oculto": f"item_{oculto}", "inexistente": "item_999", "id_invalido": "abc", "retida": "retida_1"}[caso]

    resposta = entrar(OUTRA_PESSOA).post(f"/api/itens/{id_}/contato", json={"mensagem": MENSAGEM})

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "NAO_ENCONTRADO"
    assert falso.enviadas == []


@pytest.mark.parametrize(
    "corpo",
    [
        {},
        {"mensagem": None},
        {"mensagem": 123},
        {"mensagem": "curta"},
        {"mensagem": "         a          "},
        {"mensagem": "x" * 2001},
        ["mensagem"],
    ],
    ids=["sem-campo", "nulo", "numero", "curta", "so-espacos", "longa", "lista"],
)
def test_mensagem_vazia_ou_acima_do_limite_responde_400(cliente, entrar, con, corpo):
    falso = EnvioFalso()
    cliente.app.state.envio = falso
    item = criar_item(con)

    resposta = entrar(OUTRA_PESSOA).post(f"/api/itens/item_{item}/contato", json=corpo)

    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "PARAMETROS_INVALIDOS"
    assert falso.enviadas == []
    assert _eventos_de_contato(con, item) == []


def test_mensagem_nos_limites_e_aceita(cliente, entrar, con):
    falso = EnvioFalso()
    cliente.app.state.envio = falso
    item = criar_item(con)
    sessao = entrar(OUTRA_PESSOA)

    assert sessao.post(f"/api/itens/item_{item}/contato", json={"mensagem": "x" * 10}).status_code == 202
    assert sessao.post(f"/api/itens/item_{item}/contato", json={"mensagem": "x" * 2000}).status_code == 202
    assert len(falso.enviadas) == 2


def test_corpo_que_nao_e_json_responde_400(cliente, entrar, con):
    item = criar_item(con)
    resposta = entrar(OUTRA_PESSOA).post(
        f"/api/itens/item_{item}/contato", content=b"oi", headers={"content-type": "application/json"}
    )
    assert resposta.status_code == 400


def test_campo_de_email_no_corpo_e_ignorado(cliente, entrar, con):
    """Não há campo de e-mail no contrato: o Reply-To é sempre o da sessão."""
    falso = EnvioFalso()
    cliente.app.state.envio = falso
    item = criar_item(con)

    entrar(OUTRA_PESSOA).post(
        f"/api/itens/item_{item}/contato",
        json={"mensagem": MENSAGEM, "email": "fic.impostor@cin.ufpe.br", "responder_para": "fic.impostor@cin.ufpe.br"},
    )

    [enviada] = falso.enviadas
    assert enviada.responder_para == OUTRA_PESSOA
    assert enviada.destinatario == AUTORA


# ---------------------------------------------------------------------------
# Falhas de envio → 502 ENVIO_FALHOU
# ---------------------------------------------------------------------------


def test_falha_no_envio_responde_502_e_nao_registra_evento(cliente, entrar, con):
    cliente.app.state.envio = EnvioFalso(falhar=True)
    item = criar_item(con)

    resposta = entrar(OUTRA_PESSOA).post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM})

    assert resposta.status_code == 502
    assert resposta.json() == {
        "codigo": "ENVIO_FALHOU",
        "mensagem": "Não foi possível enviar a mensagem agora. Tente mais tarde.",
    }
    assert _eventos_de_contato(con, item) == []


@pytest.mark.parametrize("endereco", ["", "   ", "sem-arroba"])
def test_item_sem_endereco_do_autor_responde_502_com_mensagem_honesta(cliente, entrar, con, endereco):
    falso = EnvioFalso()
    cliente.app.state.envio = falso
    item = criar_item(con, autor_email=endereco)

    resposta = entrar(OUTRA_PESSOA).post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM})

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "ENVIO_FALHOU"
    assert "não tem um endereço para contato" in resposta.json()["mensagem"]
    assert "sem-arroba" not in resposta.text
    assert falso.enviadas == []
    assert _eventos_de_contato(con, item) == []


def test_modo_arquivo_com_pasta_inacessivel_responde_502(url_banco, con, tmp_path):
    from fastapi.testclient import TestClient

    from api.testes.conftest import cookie_de

    ocupado = tmp_path / "e-um-arquivo"
    ocupado.write_text("não é pasta")
    config = fazer_config(url_banco, email_modo_envio="arquivo", email_arquivo_dir=str(ocupado / "emails"))
    item = criar_item(con)
    with TestClient(criar_app(config)) as cliente:
        cliente.cookies.update(cookie_de(config, OUTRA_PESSOA))
        resposta = cliente.post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM})

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "ENVIO_FALHOU"
    assert _eventos_de_contato(con, item) == []


# ---------------------------------------------------------------------------
# Modo smtp (com SMTP falso: o real nunca roda em teste)
# ---------------------------------------------------------------------------


class SmtpFalso:
    instancias: list["SmtpFalso"] = []
    falhar_no_login = False

    def __init__(self, host, porta, timeout=None):
        self.host, self.porta, self.timeout = host, porta, timeout
        self.passos: list[str] = []
        self.enviada = None
        SmtpFalso.instancias.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.passos.append("quit")
        return False

    def starttls(self):
        self.passos.append("starttls")

    def login(self, usuario, senha):
        self.passos.append(f"login:{usuario}")
        if SmtpFalso.falhar_no_login:
            raise smtplib.SMTPAuthenticationError(535, b"recusado")

    def send_message(self, mensagem):
        self.passos.append("send_message")
        self.enviada = mensagem


def _config_smtp(url_banco, **extra) -> modulo_config.Config:
    valores = dict(
        email_modo_envio="smtp",
        email_remetente=REMETENTE_PROJETO,
        smtp_host="localhost",
        smtp_port=2525,
        smtp_usuario=REMETENTE_PROJETO,
        smtp_senha="senha-so-do-teste",
    )
    valores.update(extra)
    return fazer_config(url_banco, **valores)


@pytest.fixture
def smtp_falso(monkeypatch):
    SmtpFalso.instancias = []
    SmtpFalso.falhar_no_login = False
    monkeypatch.setattr(envio.smtplib, "SMTP", SmtpFalso)
    return SmtpFalso


def test_modo_smtp_usa_starttls_login_e_envia_ao_autor(url_banco, con, smtp_falso):
    from fastapi.testclient import TestClient

    from api.testes.conftest import cookie_de

    config = _config_smtp(url_banco)
    item = criar_item(con)
    with TestClient(criar_app(config)) as cliente:
        cliente.cookies.update(cookie_de(config, OUTRA_PESSOA))
        resposta = cliente.post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM})

    assert resposta.status_code == 202
    [conexao] = smtp_falso.instancias
    assert (conexao.host, conexao.porta) == ("localhost", 2525)
    assert conexao.passos == ["starttls", f"login:{REMETENTE_PROJETO}", "send_message", "quit"]
    assert conexao.enviada["To"] == AUTORA
    assert conexao.enviada["Reply-To"] == OUTRA_PESSOA


def test_modo_smtp_com_falha_responde_502_sem_detalhe_do_servidor(url_banco, con, smtp_falso):
    from fastapi.testclient import TestClient

    from api.testes.conftest import cookie_de

    smtp_falso.falhar_no_login = True
    config = _config_smtp(url_banco)
    item = criar_item(con)
    with TestClient(criar_app(config)) as cliente:
        cliente.cookies.update(cookie_de(config, OUTRA_PESSOA))
        resposta = cliente.post(f"/api/itens/item_{item}/contato", json={"mensagem": MENSAGEM})

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "ENVIO_FALHOU"
    assert "535" not in resposta.text and "recusado" not in resposta.text
    assert _eventos_de_contato(con, item) == []


def test_smtp_de_verdade_nunca_roda_em_teste():
    """A fixture autouse `smtp_proibido` troca smtplib.SMTP por uma função que falha o teste."""
    with pytest.raises(AssertionError):
        smtplib.SMTP("localhost", 25)
    with pytest.raises(AssertionError):
        smtplib.SMTP_SSL("localhost", 465)


@pytest.mark.parametrize(
    "faltando",
    [
        {"email_remetente": ""},
        {"smtp_host": ""},
        {"smtp_usuario": ""},
        {"smtp_senha": ""},
        {"email_remetente": "troque-por-conta-do-projeto@exemplo.invalid"},
        {"smtp_senha": "troque-por-senha-de-app"},
    ],
    ids=["remetente", "host", "usuario", "senha", "remetente-exemplo", "senha-exemplo"],
)
def test_modo_smtp_sem_credenciais_reais_nao_sobe(url_banco, faltando):
    with pytest.raises(modulo_config.ConfiguracaoInvalida):
        _config_smtp(url_banco, **faltando)


def test_modo_padrao_e_nao_enviar(url_banco):
    config = fazer_config(url_banco)
    assert config.email_modo_envio == "nao_enviar"
    assert isinstance(envio.criar(config), envio.NaoEnviar)


def test_senha_smtp_nao_aparece_na_representacao_da_config(url_banco):
    assert "senha-so-do-teste" not in repr(_config_smtp(url_banco))
