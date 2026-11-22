"""Extração dos dados do item (US-03): objeto, local, data e contato.

- **Objeto, local, data, contato:** GLiNER (`gliner`, modelo multilíngue), um modelo de
  reconhecimento de entidades que roda local, sem rede depois do primeiro download. Não é LLM e não
  gera texto: só marca trechos que já estão na mensagem (ADR-009). O modelo fica em cache no
  diretório de `HF_HOME` (no Docker, um volume).
- **Local:** além do GLiNER, regras fechadas reconhecem salas (`E132`) e os apelidos da tabela
  `local` ("grad5", "Grad02", "lab de harware"), normalizados para o nome oficial. O que não é
  reconhecido entra como texto livre ("banheiro masculino do 2º andar do bloco E").
- **Localização** (onde o objeto está agora) **nunca é inferida** (invariante 3). Só uma frase
  explícita do autor de um achado, de uma lista fechada de padrões, preenche o campo.
- Campo não identificado fica vazio. Nada é inventado. Contato e data não viram coluna: o evento
  registra só se havia contato, nunca o contato (invariante 1).
- Nome de pessoa marcado pelo modelo é retirado da descrição, que é pública (caso 14).
"""
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from worker.texto import limpar_assunto, normalizar

log = logging.getLogger("worker.extrator")

MODELO_PADRAO = "urchade/gliner_multi-v2.1"
ROTULOS = ["objeto", "local", "data", "contato", "pessoa"]
LIMIAR = float(os.environ.get("WORKER_GLINER_LIMIAR", "0.4"))


class ModeloIndisponivel(Exception):
    """Sem rede e sem cache, ou o modelo não carregou. O item publica só com a classificação."""


# ----------------------------------------------------------------------------- locais
# Apelidos de uso → nome da tabela `local` (shared/migrations/003). Ordem importa: o primeiro casa.
APELIDOS_LOCAIS: List[Tuple[str, str]] = [
    (r"\bgrad\s*0?1\b", "Grad 1"),
    (r"\bgrad\s*0?2\b", "Grad 2"),
    (r"\bgrad\s*0?3\b", "Grad 3"),
    (r"\bgrad\s*0?4\b", "Grad 4"),
    (r"\bgrad\s*0?5\b", "Grad 5"),
    (r"\blab(?:oratorio)?\.?\s+(?:de\s+)?har\w{0,2}ware\b", "Laboratório de hardware"),
    (r"\blab(?:oratorio)?\.?\s+(?:de\s+)?pos(?:-graduacao)?\b", "Laboratório de pós-graduação"),
    (r"\banfiteatro\b", "Anfiteatro"),
    (r"\bgerinfra\b|\bb\s?-?021\b", "Gerinfra (sala B021)"),
]
_SALA = re.compile(r"\b([a-e])\s?-?(\d{3})\b")
# Trechos que o modelo às vezes marca como local e não ajudam a achar nada.
LOCAIS_GENERICOS = {"cin", "aqui", "la", "ali", "casa", "local", "no local", "ufpe", "sala", "centro de informatica"}


def locais_por_regra(texto: str) -> List[str]:
    """Nomes da tabela `local` e salas no formato `E132` encontrados no texto."""
    n = normalizar(texto)
    achados: List[str] = []
    for padrao, nome in APELIDOS_LOCAIS:
        if re.search(padrao, n) and nome not in achados:
            achados.append(nome)
    for bloco, numero in _SALA.findall(n):
        sala = f"{bloco.upper()}{numero}"
        if sala not in achados:
            achados.append(sala)
    return achados


def normalizar_local(trecho: str) -> str:
    """'grad 05' → 'Grad 5'; 'lab de harware' → 'Laboratório de hardware'; o resto fica como veio."""
    n = normalizar(trecho)
    for padrao, nome in APELIDOS_LOCAIS:
        if re.fullmatch(r"(?:(?:o|a|no|na|do|da|sala|perto do|perto da)\s+)?(?:" + padrao + r")", n):
            return nome
    m = _SALA.fullmatch(n) or re.fullmatch(r"(?:sala\s+)?([a-e])\s?-?(\d{3})", n)
    if m:
        return f"{m.group(1).upper()}{m.group(2)}"
    return trecho.strip(" .,;:")


def juntar_locais(por_regra: List[str], do_modelo: List[str]) -> List[str]:
    """Une as duas fontes sem repetir: um trecho que já contém (ou está contido em) outro fica só uma vez,
    e o nome oficial ganha do texto livre equivalente."""
    resultado: List[str] = list(por_regra)
    for trecho in do_modelo:
        nome = normalizar_local(trecho)
        n = normalizar(nome)
        if not n or n in LOCAIS_GENERICOS or len(n) < 3:
            continue
        if any(n == normalizar(r) for r in resultado):
            continue
        # Texto livre que só repete um nome oficial já presente ("no Grad 5") não entra de novo.
        if any(normalizar(r) in n and len(n) - len(normalizar(r)) <= 4 for r in resultado):
            continue
        resultado.append(nome)
    return resultado


# ----------------------------------------------------------------------------- localização
# Padrões fechados (worker/AGENTS.md e PR do W3). Só valem para frase do AUTOR de um ACHADO.
SETORES: List[Tuple[str, str]] = [
    (r"secretaria de graduacao|secgrad", "SecGrad"),
    (r"gerinfra", "Gerinfra"),
    (r"coordenacao", "Coordenação"),
]
_SETOR = "|".join(p for p, _ in SETORES)
PADROES_LOCALIZACAO: List[Tuple[str, str]] = [
    ("com um setor", r"\b(?:deixei|deixamos|entreguei|levei|esta|estao|se encontra)\s+(?:(?:o|a|os|as|ele|ela|eles|elas)\s+)?(?:na|no|com a|com o|para a|para o|pra)\s+(?P<setor>" + _SETOR + r")\b"),
    ("com um setor", r"\b(?:disponivel |disponiveis )?para retirada (?:na|no)\s+(?P<setor>" + _SETOR + r")\b"),
    ("com um setor", r"\b(?:deixei|entreguei|esta|ficou)\s+(?:(?:o|a|ele|ela)\s+)?com o (?P<professor>prof(?:essor|\.)?\s+[a-z]+)\b"),
    ("com quem achou", r"\b(?:esta|ta|estao|tao|ficou|fica|deixei|guardei)\s+comigo\b"),
    ("com quem achou", r"\bguardei\s+(?:na|no)\s+(?:minha|meu)\b"),
    ("com quem achou", r"\blevei\b[\w ,]{0,40}\b(?:para|pra)\s+casa\b"),
    ("com quem achou", r"\bcomigo\s+para\s+(?:eu\s+)?(?:lhe\s+|te\s+)?(?:entregar|devolver)\b"),
    ("no local", r"\b(?:deixei|deixamos|ficou)\s+(?:la|no local|onde estava)\b"),
    ("no local", r"\b(?:esta|se encontra|continua|permanece)\s+(?:ainda\s+)?no local\b"),
]


def localizacao_declarada(texto_do_autor: str) -> Tuple[Optional[str], Optional[str]]:
    """Devolve (localizacao, setor) se o texto declara onde o objeto está, senão (None, None).

    Se houver mais de uma declaração, vale a última do texto (é a mais recente)."""
    n = normalizar(texto_do_autor)
    melhor: Optional[Tuple[int, str, Optional[str]]] = None
    for valor, padrao in PADROES_LOCALIZACAO:
        for m in re.finditer(padrao, n):
            setor = None
            if valor == "com um setor":
                grupos = m.groupdict()
                if grupos.get("setor"):
                    setor = next(nome for p, nome in SETORES if re.fullmatch(p, grupos["setor"]))
                elif grupos.get("professor"):
                    setor = "professor " + grupos["professor"].split()[-1].capitalize()
            if melhor is None or m.start() >= melhor[0]:
                melhor = (m.start(), valor, setor)
    if melhor is None:
        return None, None
    return melhor[1], melhor[2]


# ----------------------------------------------------------------------------- modelo
class ModeloGliner:
    """Carrega o GLiNER na primeira chamada. Falha de carga vira `ModeloIndisponivel`."""

    def __init__(self, nome: str = None):
        self.nome = nome or os.environ.get("WORKER_GLINER_MODELO", MODELO_PADRAO)
        self._modelo = None

    def _carregar(self):
        if self._modelo is None:
            try:
                from gliner import GLiNER

                self._modelo = GLiNER.from_pretrained(self.nome)
            except Exception as erro:
                raise ModeloIndisponivel(f"não foi possível carregar {self.nome} ({type(erro).__name__})") from None
        return self._modelo

    def __call__(self, texto: str, rotulos: List[str]) -> List[Dict]:
        modelo = self._carregar()
        try:
            return modelo.predict_entities(texto, rotulos, threshold=LIMIAR)
        except Exception as erro:
            raise ModeloIndisponivel(f"falha ao extrair ({type(erro).__name__})") from None


class ModeloSimulado:
    """Não marca nada. Usado nos testes (sem rede e sem baixar 1 GB) e quando WORKER_EXTRATOR=simulado.
    Com ele, só as regras fechadas (locais e localização) funcionam."""

    nome = "simulado"

    def __call__(self, texto: str, rotulos: List[str]) -> List[Dict]:
        return []


def criar_modelo():
    """WORKER_EXTRATOR=gliner (padrão) ou simulado."""
    escolha = os.environ.get("WORKER_EXTRATOR", "gliner").strip().lower()
    if escolha == "simulado":
        log.warning("extração com modelo simulado: só as regras fechadas preenchem campos")
        return ModeloSimulado()
    return ModeloGliner()


# ----------------------------------------------------------------------------- extração
@dataclass
class Extracao:
    objetos: List[str] = field(default_factory=list)
    locais: List[str] = field(default_factory=list)
    datas: List[str] = field(default_factory=list)
    tem_contato: bool = False
    localizacao: Optional[str] = None
    setor: Optional[str] = None
    descricao: Optional[str] = None

    def detalhes(self) -> dict:
        """O que vai para o evento `extracao`. Sem contato e sem nome de pessoa."""
        return {
            "objetos": self.objetos,
            "locais": self.locais,
            "datas": self.datas,
            "tem_contato": self.tem_contato,
            "localizacao": self.localizacao,
            "setor": self.setor,
            "descricao": self.descricao,
        }


def _unicos(trechos: List[str]) -> List[str]:
    vistos, saida = set(), []
    for t in trechos:
        t = " ".join(t.split()).strip(" .,;:!?")
        n = normalizar(t)
        if n and n not in vistos:
            vistos.add(n)
            saida.append(t)
    return saida


def _sem_contidos(trechos: List[str]) -> List[str]:
    """'garrafa' some se 'garrafa azul' também foi marcada."""
    n = [normalizar(t) for t in trechos]
    return [t for i, t in enumerate(trechos) if not any(i != j and n[i] != n[j] and n[i] in n[j] for j in range(len(n)))]


def enumerar(objetos: List[str]) -> Optional[str]:
    """['boné bege NY', "garrafa d'água preta"] → "Boné bege NY e garrafa d'água preta"."""
    if not objetos:
        return None
    texto = objetos[0] if len(objetos) == 1 else ", ".join(objetos[:-1]) + " e " + objetos[-1]
    return texto[0].upper() + texto[1:]


_ADJETIVO_DE_DIRECAO = re.compile(r"\s*\b(?:perdid|achad|encontrad|esquecid)[oa]s?\b", re.IGNORECASE)
_CAUDA_DE_LOCAL = re.compile(r"\s+(?:no|na|nos|nas|em|perto d[oa]|ao lado d[oa])\s+(.+)$", re.IGNORECASE)
_PALAVRA_DE_LUGAR = re.compile(r"\b(?:sala|grad|bloco|mezanino|fileira|mesa|mesinha|lab\w*|corredor|banheiro|cantina|auditorio|biblioteca|secgrad|estacionamento|e\d{3})")
# O modelo às vezes marca como objeto um pronome ou um pedaço de frase ("Esse aparelho",
# "disponível para retirada"): isso não serve de descrição.
_NAO_E_OBJETO = re.compile(r"^(?:esse|essa|este|esta|isso|isto|ele|ela|o mesmo|a mesma)\b|\bdisponive|\bretirada\b")
_COMECA_COM_VERBO = re.compile(r"^(?:perdi|esqueci|encontrei|achei|alguem|retirando|procuro|procura-se)\b")


def _sem_cauda_de_local(texto: str) -> str:
    """"Batom no grad 4" → "Batom": o local já tem campo próprio."""
    corte = _CAUDA_DE_LOCAL.search(texto)
    if corte:
        cauda = normalizar(corte.group(1))
        if locais_por_regra(cauda) or _PALAVRA_DE_LUGAR.search(cauda):
            return texto[: corte.start()].strip(" .,;:-")
    return texto


def descricao_do_assunto(assunto_limpo: str, objetos: List[str]) -> Optional[str]:
    """O assunto costuma ser a melhor descrição curta ("Mouse Preto Logitech G305"), quando ele
    nomeia um dos objetos extraídos, é curto, não é frase ("Perdi uma garrafa...") nem está todo em
    maiúsculas. Tira "perdido/achado" do texto: num achado, "Telefone perdido" confunde."""
    if not assunto_limpo or not objetos or assunto_limpo.isupper() or len(assunto_limpo) > 70:
        return None
    n = normalizar(assunto_limpo)
    if _COMECA_COM_VERBO.match(n) or not any(normalizar(o) in n for o in objetos):
        return None
    texto = " ".join(_ADJETIVO_DE_DIRECAO.sub("", assunto_limpo).split()).strip(" .,;:-")
    texto = _sem_cauda_de_local(texto)
    return (texto[0].upper() + texto[1:]) if texto else None


def _tirar_pessoas(texto: str, pessoas: List[str]) -> str:
    for p in sorted(pessoas, key=len, reverse=True):
        texto = re.sub(r"\s*(?:de|do|da)?\s*" + re.escape(p), "", texto, flags=re.IGNORECASE)
    return " ".join(texto.split())


def extrair(
    assunto: str,
    corpo_limpo: str,
    tipo: str,
    modelo: Callable[[str, List[str]], List[Dict]],
) -> Extracao:
    """Extrai do anúncio. Levanta `ModeloIndisponivel` se o modelo não estiver disponível.

    A localização sai só das regras (não do modelo) e só para achado: é o autor do anúncio dizendo
    onde deixou o que achou."""
    assunto_limpo = limpar_assunto(assunto)
    texto = "\n".join(t for t in (assunto_limpo, corpo_limpo) if t)
    entidades = modelo(texto, ROTULOS) if texto else []

    por_rotulo: Dict[str, List[str]] = {r: [] for r in ROTULOS}
    for e in entidades:
        if e.get("label") in por_rotulo:
            por_rotulo[e["label"]].append(e.get("text", ""))
    pessoas = _unicos(por_rotulo["pessoa"])

    objetos = []
    for o in _unicos(por_rotulo["objeto"]):
        limpo = " ".join(_ADJETIVO_DE_DIRECAO.sub("", _tirar_pessoas(o, pessoas)).split()).strip(" .,;:")
        limpo = _sem_cauda_de_local(limpo)
        if limpo and not _NAO_E_OBJETO.search(normalizar(limpo)):
            objetos.append(limpo)
    objetos = _sem_contidos(_unicos(objetos))

    locais = juntar_locais(locais_por_regra(texto), _sem_contidos(_unicos(por_rotulo["local"])))

    localizacao, setor = (None, None)
    if tipo == "achado":
        localizacao, setor = localizacao_declarada(corpo_limpo)

    descricao = descricao_do_assunto(_tirar_pessoas(assunto_limpo, pessoas), objetos) or enumerar(objetos)
    if descricao is None and assunto_limpo:
        descricao = _tirar_pessoas(assunto_limpo, pessoas) or None

    return Extracao(
        objetos=objetos,
        locais=locais,
        datas=_unicos(por_rotulo["data"]),
        tem_contato=bool(por_rotulo["contato"]),
        localizacao=localizacao,
        setor=setor,
        descricao=descricao,
    )
