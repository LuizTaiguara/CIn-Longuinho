# api/ — API REST (Python, FastAPI)

Vale além do `AGENTS.md` da raiz. Backend: Miguel (revisor do contrato em `shared/`).

## O que é

- A **única porta do site para os dados** (invariante 8). O site nunca fala com o banco nem com o worker.
- Implementa **exatamente** `shared/openapi.yaml`, com todas as rotas sob `/api` (`API_PREFIX`).
- Python, como o worker (ADR-008). Nesta rodada a camada de dados está duplicada
  (`api/banco.py` e `worker/banco.py`); unificar em `shared/` é dívida registrada.

## Mapa

| Arquivo | Faz |
|---|---|
| `main.py` | `criar_app()`: monta as rotas sob `API_PREFIX` e os tratadores de erro |
| `config.py` | Lê o ambiente (`.env`). Recusa subir com configuração perigosa |
| `banco.py` | Pool do psycopg 3 e uma função por consulta nomeada |
| `respostas.py` | Monta cada resposta do contrato campo a campo (lista branca) |
| `sessao.py` | Cookie de sessão assinado, 7 dias, `HttpOnly`, `SameSite=Lax` |
| `erros.py` | Formato `Erro` (`{codigo, mensagem}`) e os códigos do contrato |
| `rotas/` | Uma rota por função, agrupadas por recurso |
| `testes/` | pytest + `TestClient`, contra um Postgres de verdade |

## Regras (as invariantes, materializadas aqui)

1. **E-mail nunca sai** (invariante 1). As consultas de leitura não trazem `autor_email` nem
   `remetente` para o Python: a autoria é comparada dentro do SQL. As respostas são montadas por
   lista branca em `respostas.py`. Nenhum erro ecoa o valor recebido. Há teste que procura o
   endereço da fixture em todo corpo, cabeçalho e log.
2. **`situacao` só avança** (invariante 2). A API confere a situação **antes** do `UPDATE`; o
   trigger do banco é rede de segurança. Evento fora de ordem é gravado com `aplicado = FALSE`.
4. **Nada é apagado** (invariante 4). Não há rota `DELETE`. Remover é ocultar, e ocultar não volta.
5. **Visibilidade no servidor** (invariante 5). Oculto, retido e inexistente devolvem o mesmo `404`.
   As duas exceções vivem só em `GET /eu/itens`, para o próprio autor.
9. **Sem credencial em código** (invariante 9). Tudo vem do ambiente; ver `.env.example`.

Mais:
- Sem sessão, a busca **nunca** consulta `mensagem_bruta` (US-04).
- Não invente campo no contrato. Se precisar, é `shared/` (revisão do Miguel) e, se mudar o que o
  usuário vê, é decisão do PO.

## Comandos

Rode da raiz do repositório, com Python 3.12.

| Para… | Comando |
|---|---|
| Instalar | `python3.12 -m venv api/.venv && api/.venv/bin/pip install -r api/requirements.txt` |
| Subir o banco | `docker compose up -d banco` |
| Rodar (desenvolvimento) | `api/.venv/bin/uvicorn api.main:app --reload --port 8000` |
| Rodar (contêiner) | `docker compose up -d api` |
| Testar | `api/.venv/bin/python -m pytest api/testes` |
| Testar um arquivo | `api/.venv/bin/python -m pytest api/testes/test_catalogo.py -q` |

Os testes apagam e recriam o banco `longuinho_teste_api` (ou o de `DATABASE_URL_TESTE`, que
precisa ter "teste" no nome), aplicam `shared/migrations/*.sql` e limpam as tabelas entre testes.
Não precisam de internet nem de credencial.
