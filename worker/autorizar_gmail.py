"""Autoriza o worker a ler a conta Gmail do projeto. Roda uma vez, numa máquina com navegador:

    python -m worker.autorizar_gmail

Lê o client OAuth (tipo "app para computador") de `GMAIL_PROJECT_CREDENTIALS_FILE`, abre o
navegador para a conta do projeto consentir o acesso **só de leitura** e grava o token em
`GMAIL_TOKEN_FILE` (padrão `worker/.segredos/token.json`, fora do Git). O worker renova o token
sozinho; se ele for revogado, o ciclo registra "credencial inválida" e é só rodar isto de novo.
"""
import os
import sys
from pathlib import Path

from worker.config import carregar_dotenv
from worker.leitor_gmail import ESCOPOS

TOKEN_PADRAO = "worker/.segredos/token.json"


def main() -> int:
    carregar_dotenv()
    credenciais = os.environ.get("GMAIL_PROJECT_CREDENTIALS_FILE", "")
    token = Path(os.environ.get("GMAIL_TOKEN_FILE") or TOKEN_PADRAO)
    if not credenciais or not Path(credenciais).is_file():
        print("GMAIL_PROJECT_CREDENTIALS_FILE não aponta para o JSON do client OAuth.", file=sys.stderr)
        return 1
    from google_auth_oauthlib.flow import InstalledAppFlow

    fluxo = InstalledAppFlow.from_client_secrets_file(credenciais, ESCOPOS)
    resultado = fluxo.run_local_server(port=0, prompt="consent", access_type="offline")
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(resultado.to_json())
    token.chmod(0o600)
    print(f"Token gravado em {token}. Não commite este arquivo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
