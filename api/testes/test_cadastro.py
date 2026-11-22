"""US-06: cadastrar um achado ou uma perda pelo site, com foto opcional."""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from PIL import Image

from api.rotas.cadastro import novo_codigo
from api.testes.contrato import conferir_resposta
from api.testes.dados import AUTORA, OUTRA_PESSOA, criar_item

ACHADO = {
    "tipo": "achado",
    "descricao": "Guarda-chuva preto com cabo de madeira",
    "local": ["Anfiteatro"],
    "localizacao": "com um setor",
    "setor": "SecGrad",
}


def imagem(formato: str = "JPEG", tamanho=(40, 30), exif: bytes | None = None) -> bytes:
    saida = io.BytesIO()
    opcoes = {"exif": exif} if exif else {}
    Image.new("RGB", tamanho, (200, 30, 30)).save(saida, format=formato, **opcoes)
    return saida.getvalue()


def enviar_foto(cliente, item_id: str, conteudo: bytes, nome="foto.jpg", tipo="image/jpeg"):
    return cliente.post(f"/api/itens/{item_id}/foto", files={"foto": (nome, conteudo, tipo)})


# --- Dado que não entrei com a minha conta do CIn ----------------------------------------------


def test_cadastro_sem_sessao_devolve_401(cliente, con):
    resposta = cliente.post("/api/itens", json=ACHADO)
    assert resposta.status_code == 401
    conferir_resposta(resposta, "POST", "/itens")
    assert con.execute("SELECT count(*) AS n FROM item").fetchone()["n"] == 0


# --- Dado que preenchi os campos obrigatórios / Quando envio o formulário ----------------------


def test_achado_e_publicado_na_hora_sem_classificacao_e_com_o_autor_da_sessao(entrar, con):
    cliente = entrar(AUTORA)

    resposta = cliente.post("/api/itens", json=ACHADO)

    assert resposta.status_code == 201
    conferir_resposta(resposta, "POST", "/itens")
    item = resposta.json()
    assert item["tipo"] == "achado" and item["situacao"] == "aberto"
    assert item["localizacao"] == "com um setor" and item["setor"] == "SecGrad"
    assert item["pode_gerir"] is True and item["texto_original"] is None
    assert [i["id"] for i in entrar(None).get("/api/itens").json()["itens"]] == [item["id"]]

    numero = int(item["id"].removeprefix("item_"))
    linha = con.execute("SELECT origem, codigo, thread_id, autor_email, revisar FROM item WHERE id = %s", [numero]).fetchone()
    assert linha["origem"] == "site" and linha["thread_id"] is None and linha["revisar"] is False
    assert linha["autor_email"] == AUTORA
    assert re.fullmatch(r"AP-[A-Z2-7]{6}", linha["codigo"])
    evento = con.execute("SELECT tipo_evento, fonte, aplicado FROM evento WHERE item_id = %s", [numero]).fetchone()
    assert evento == {"tipo_evento": "criacao", "fonte": "cadastro pelo site", "aplicado": True}
    assert con.execute("SELECT count(*) AS n FROM quarentena").fetchone()["n"] == 0


def test_item_cadastrado_aparece_em_meus_anuncios_como_ainda_nao_foi_para_a_lista(entrar, con):
    cliente = entrar(AUTORA)
    item = cliente.post("/api/itens", json=ACHADO).json()

    meu = cliente.get("/api/eu/itens").json()[0]

    assert meu["id"] == item["id"]
    assert meu["origem"] == "site" and meu["foi_para_a_lista"] is False
    assert re.fullmatch(r"AP-[A-Z2-7]{6}", meu["codigo"])


def test_perda_aceita_varios_locais_e_ignora_onde_o_objeto_esta(entrar, con):
    resposta = entrar(AUTORA).post(
        "/api/itens",
        json={"tipo": "perdido", "descricao": "Caderno verde", "local": ["Grad 1", "Grad 5"],
              "localizacao": "no local", "setor": "SecGrad"},
    )

    assert resposta.status_code == 201
    item = resposta.json()
    assert item["local"] == ["Grad 1", "Grad 5"]
    assert item["localizacao"] is None and item["setor"] is None


def test_local_fora_da_lista_predefinida_e_aceito_como_outro(entrar, con):
    resposta = entrar(AUTORA).post("/api/itens", json={**ACHADO, "local": ["Cantina do CIn"]})
    assert resposta.status_code == 201
    assert resposta.json()["local"] == ["Cantina do CIn"]


def test_autor_vem_da_sessao_mesmo_que_o_corpo_traga_outro(entrar, con):
    entrar(AUTORA).post("/api/itens", json={**ACHADO, "autor_email": OUTRA_PESSOA})
    assert con.execute("SELECT autor_email FROM item").fetchone()["autor_email"] == AUTORA


# --- Dado que deixei um campo obrigatório vazio ------------------------------------------------


def test_achado_sem_onde_esta_devolve_localizacao_obrigatoria(entrar, con):
    for corpo in ({k: v for k, v in ACHADO.items() if k != "localizacao"}, {**ACHADO, "localizacao": None}):
        resposta = entrar(AUTORA).post("/api/itens", json=corpo)
        assert resposta.status_code == 400
        conferir_resposta(resposta, "POST", "/itens")
        assert resposta.json()["codigo"] == "LOCALIZACAO_OBRIGATORIA"
        assert "localizacao" in resposta.json()["mensagem"]


@pytest.mark.parametrize(
    "mudanca,campo",
    [
        ({"tipo": "doado"}, "tipo"),
        ({"descricao": "abc"}, "descricao"),
        ({"descricao": "    "}, "descricao"),
        ({"local": []}, "local"),
        ({"local": "Grad 5"}, "local"),
        ({"local": [""]}, "local"),
        ({"localizacao": "na portaria"}, "localizacao"),
    ],
)
def test_campo_obrigatorio_invalido_devolve_400_nomeando_o_campo(entrar, con, mudanca, campo):
    resposta = entrar(AUTORA).post("/api/itens", json={**ACHADO, **mudanca})
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "PARAMETROS_INVALIDOS"
    assert f"`{campo}`" in resposta.json()["mensagem"]


# --- Envio duplicado (clique duplo) ------------------------------------------------------------


def test_clique_duplo_cria_um_item_so(entrar, con):
    cliente = entrar(AUTORA)

    primeiro = cliente.post("/api/itens", json=ACHADO)
    segundo = cliente.post("/api/itens", json=ACHADO)

    assert primeiro.status_code == segundo.status_code == 201
    assert primeiro.json()["id"] == segundo.json()["id"]
    assert con.execute("SELECT count(*) AS n FROM item").fetchone()["n"] == 1
    assert con.execute("SELECT count(*) AS n FROM evento").fetchone()["n"] == 1


def test_mesmo_cadastro_depois_de_30_segundos_cria_outro_item(entrar, con):
    cliente = entrar(AUTORA)
    cliente.post("/api/itens", json=ACHADO)
    con.execute("UPDATE item SET criado_em = criado_em - interval '31 seconds'")

    cliente.post("/api/itens", json=ACHADO)

    assert con.execute("SELECT count(*) AS n FROM item").fetchone()["n"] == 2


def test_cadastros_iguais_de_pessoas_diferentes_sao_itens_diferentes(entrar, con):
    entrar(AUTORA).post("/api/itens", json=ACHADO)
    entrar(OUTRA_PESSOA).post("/api/itens", json=ACHADO)
    assert con.execute("SELECT count(*) AS n FROM item").fetchone()["n"] == 2


def test_codigo_tem_o_formato_ap_e_seis_caracteres_base32():
    codigos = {novo_codigo() for _ in range(500)}
    assert all(re.fullmatch(r"AP-[A-Z2-7]{6}", c) for c in codigos)
    assert len(codigos) > 490


# --- Foto (opcional) ---------------------------------------------------------------------------


@pytest.fixture
def item_do_site(entrar, con):
    return entrar(AUTORA).post("/api/itens", json=ACHADO).json()["id"]


@pytest.mark.parametrize("formato,extensao,tipo", [("JPEG", "jpg", "image/jpeg"), ("PNG", "png", "image/png"), ("WEBP", "webp", "image/webp")])
def test_foto_jpeg_png_webp_e_aceita_e_servida_pela_api(entrar, con, item_do_site, formato, extensao, tipo):
    cliente = entrar(AUTORA)

    resposta = enviar_foto(cliente, item_do_site, imagem(formato), nome="qualquer.bin", tipo="application/octet-stream")

    assert resposta.status_code == 200
    conferir_resposta(resposta, "POST", "/itens/{id}/foto")
    url = resposta.json()["foto_url"]
    assert re.fullmatch(rf"/api/fotos/[0-9a-f]{{32}}\.{extensao}", url)
    servida = entrar(None).get(url)
    assert servida.status_code == 200
    assert servida.headers["content-type"] == tipo
    assert Image.open(io.BytesIO(servida.content)).format == formato


def test_foto_sai_sem_metadados_de_localizacao(entrar, con, item_do_site, config):
    exif = Image.Exif()
    exif[0x8825] = {1: "S", 2: (8.0, 3.0, 0.0)}  # GPSInfo
    exif[0x010F] = "Fabricante Fictício"
    original = imagem("JPEG", exif=exif.tobytes())
    assert Image.open(io.BytesIO(original)).getexif()

    url = enviar_foto(entrar(AUTORA), item_do_site, original).json()["foto_url"]

    gravada = Path(config.fotos_dir) / url.rsplit("/", 1)[1]
    assert not Image.open(gravada).getexif()


@pytest.mark.parametrize(
    "conteudo,nome",
    [
        (b"isto nao e imagem", "foto.jpg"),
        (b"", "foto.jpg"),
        (imagem("GIF"), "foto.gif"),
        (imagem("BMP"), "foto.bmp"),
        (imagem("JPEG")[:200], "foto.jpg"),
    ],
)
def test_formato_nao_aceito_devolve_foto_invalida(entrar, con, item_do_site, conteudo, nome):
    resposta = enviar_foto(entrar(AUTORA), item_do_site, conteudo, nome=nome)
    assert resposta.status_code == 400
    conferir_resposta(resposta, "POST", "/itens/{id}/foto")
    assert resposta.json()["codigo"] == "FOTO_INVALIDA"


def test_envio_sem_o_campo_foto_devolve_foto_invalida(entrar, con, item_do_site):
    resposta = entrar(AUTORA).post(f"/api/itens/{item_do_site}/foto", files={"arquivo": ("a.jpg", imagem(), "image/jpeg")})
    assert resposta.status_code == 400
    assert resposta.json()["codigo"] == "FOTO_INVALIDA"


def test_foto_acima_de_5_mb_devolve_foto_grande(entrar, con, item_do_site):
    resposta = enviar_foto(entrar(AUTORA), item_do_site, b"\xff" * (5 * 1024 * 1024 + 1))
    assert resposta.status_code == 413
    conferir_resposta(resposta, "POST", "/itens/{id}/foto")
    assert resposta.json()["codigo"] == "FOTO_GRANDE"


def test_foto_no_item_de_outra_pessoa_devolve_403_e_sem_sessao_401(entrar, con, item_do_site):
    assert enviar_foto(entrar(OUTRA_PESSOA), item_do_site, imagem()).status_code == 403
    assert enviar_foto(entrar(None), item_do_site, imagem()).status_code == 401
    assert enviar_foto(entrar(AUTORA), "item_999", imagem()).status_code == 404


def test_trocar_a_foto_mantem_o_arquivo_anterior_e_registra_a_troca(entrar, con, item_do_site, config):
    cliente = entrar(AUTORA)
    primeira = enviar_foto(cliente, item_do_site, imagem()).json()["foto_url"]
    segunda = enviar_foto(cliente, item_do_site, imagem("PNG")).json()["foto_url"]

    assert primeira != segunda
    assert (Path(config.fotos_dir) / primeira.rsplit("/", 1)[1]).is_file()
    assert entrar(None).get(primeira).status_code == 404  # não é mais a foto do item
    assert entrar(None).get(segunda).status_code == 200
    numero = int(item_do_site.removeprefix("item_"))
    ultimo = con.execute(
        "SELECT detalhes FROM evento WHERE item_id = %s AND tipo_evento = 'edicao' ORDER BY id DESC LIMIT 1", [numero]
    ).fetchone()["detalhes"]
    assert ultimo == {"antes": {"foto_url": primeira}, "depois": {"foto_url": segunda}}


def test_foto_de_item_oculto_so_e_servida_ao_autor(entrar, con, item_do_site):
    url = enviar_foto(entrar(AUTORA), item_do_site, imagem()).json()["foto_url"]
    entrar(AUTORA).post(f"/api/itens/{item_do_site}/ocultar")

    assert entrar(None).get(url).status_code == 404
    assert entrar(OUTRA_PESSOA).get(url).status_code == 404
    assert entrar(AUTORA).get(url).status_code == 200


@pytest.mark.parametrize("nome", ["..%2F..%2Fetc%2Fpasswd", "abc.jpg", "0" * 32 + ".gif", "0" * 32 + ".jpg"])
def test_nome_de_foto_invalido_ou_desconhecido_devolve_404(cliente, con, nome):
    assert cliente.get(f"/api/fotos/{nome}").status_code == 404


def test_foto_em_item_da_lista_tambem_e_aceita(entrar, con):
    numero = criar_item(con, autor_email=AUTORA)
    assert enviar_foto(entrar(AUTORA), f"item_{numero}", imagem()).status_code == 200
