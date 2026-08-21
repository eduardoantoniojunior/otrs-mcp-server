#!/usr/bin/env python3
"""
Teste de conectividade OTRS Generic Interface (Web Service MCPConnector).

Valida, na ordem:

  1. Se o SessionCreate autentica o Customer User.
  2. Se o TicketSearch funciona reutilizando a SessionID criada.

Uso:

  Por padrão, o script carrega automaticamente o arquivo ".env"
  localizado na mesma pasta do script:

    python otrs_mcp_connectivity_test.py

  Para utilizar outro arquivo:

    python otrs_mcp_connectivity_test.py --env-file caminho/outro.env

Variáveis esperadas no .env:

  OTRS_BASE_URL=https://servidor/otrs/nph-genericinterface.pl/Webservice/MCPConnector
  OTRS_USERNAME=usuario@empresa.com
  OTRS_PASSWORD=senha
  OTRS_VERIFY_SSL=true

O script nunca imprime o valor de OTRS_PASSWORD ou da SessionID.
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_dotenv(path: Path) -> None:
    """
    Carrega pares CHAVE=VALOR de um arquivo .env para os.environ.

    Variáveis que já estiverem definidas no ambiente do sistema
    não serão sobrescritas.
    """

    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")

        key = key.strip()
        value = value.strip()

        # Remove aspas simples ou duplas que envolvem todo o valor.
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        if key:
            os.environ.setdefault(key, value)


def env_bool(name: str, default: bool) -> bool:
    """Converte uma variável de ambiente para booleano."""

    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
        "sim",
    )


def post_json(
    url: str,
    payload: dict,
    verify_ssl: bool,
    timeout: int = 15,
):
    """
    Executa uma requisição HTTP POST com corpo JSON.

    Retorno:
        status, body, error
    """

    data = json.dumps(
        payload,
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OTRS-MCP-Connectivity-Test/1.0",
        },
    )

    ssl_context = None

    if url.lower().startswith("https://"):
        ssl_context = ssl.create_default_context()

        if not verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=ssl_context,
        ) as response:
            status = response.status
            body = response.read().decode(
                "utf-8",
                errors="replace",
            )

    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read().decode(
            "utf-8",
            errors="replace",
        )

    except urllib.error.URLError as error:
        reason = getattr(error, "reason", error)

        return (
            None,
            None,
            f"Falha de rede/conexão: {reason}",
        )

    except (TimeoutError, ssl.SSLError, OSError) as error:
        return (
            None,
            None,
            f"Falha de rede/TLS: {error}",
        )

    return status, body, None


def parse_json_response(
    body: str,
    operation: str,
):
    """Converte e valida uma resposta JSON do OTRS."""

    try:
        data = json.loads(body)

    except json.JSONDecodeError:
        print(
            f"[ERRO] {operation}: a resposta não é um JSON válido."
        )
        print(
            f"       Corpo bruto (primeiros 500 caracteres): "
            f"{body[:500]}"
        )
        return None

    if not isinstance(data, dict):
        print(
            f"[ERRO] {operation}: o JSON retornado possui "
            "um formato inesperado."
        )
        print(
            f"       Tipo recebido: {type(data).__name__}"
        )
        return None

    return data


def print_otrs_error(
    operation: str,
    data: dict,
) -> bool:
    """
    Mostra um erro retornado pelo OTRS.

    Retorna True quando existe erro.
    """

    if "Error" not in data:
        return False

    error_info = data.get("Error")

    if not isinstance(error_info, dict):
        error_info = {}

    error_code = error_info.get(
        "ErrorCode",
        "(não informado)",
    )

    error_message = error_info.get(
        "ErrorMessage",
        "(não informado)",
    )

    print(f"[ERRO] {operation} retornou erro de aplicação:")
    print(f"       ErrorCode:    {error_code}")
    print(f"       ErrorMessage: {error_message}")

    if error_code == "SessionCreate.AuthFail":
        print(
            "       Confirme o CustomerUserLogin e a senha."
        )
        print(
            "       O usuário deve ser o mesmo utilizado no customer.pl."
        )

    elif error_code == "TicketSearch.AuthFail":
        print(
            "       A operação foi encontrada, mas a SessionID "
            "não foi aceita."
        )
        print(
            "       No depurador do OTRS, confira se o TicketSearch "
            "recebeu:"
        )
        print(
            "       'SessionID' => '<valor da sessão>'"
        )

    elif "AccessDenied" in str(error_code):
        print(
            "       A sessão é válida, mas o Customer User não possui "
            "acesso ao recurso solicitado."
        )

    return True


def main() -> None:
    """Executa os testes de conectividade."""

    # --------------------------------------------------------------
    # Carregamento do arquivo .env
    # --------------------------------------------------------------

    env_path = Path(__file__).resolve().parent / ".env"

    args = sys.argv[1:]

    if "--env-file" in args:
        index = args.index("--env-file")

        if index + 1 >= len(args):
            print(
                "[ERRO] Informe o caminho depois de --env-file."
            )
            sys.exit(1)

        env_path = Path(args[index + 1]).expanduser()

    load_dotenv(env_path)

    env_status = (
        "encontrado"
        if env_path.is_file()
        else "NÃO encontrado"
    )

    print(
        f"[.env] Arquivo carregado: {env_path} "
        f"({env_status})"
    )

    # --------------------------------------------------------------
    # Variáveis de configuração
    # --------------------------------------------------------------

    base_url = (
        os.environ
        .get("OTRS_BASE_URL", "")
        .strip()
        .rstrip("/")
    )

    username = (
        os.environ
        .get("OTRS_USERNAME", "")
        .strip()
    )

    password = os.environ.get(
        "OTRS_PASSWORD",
        "",
    )

    verify_ssl = env_bool(
        "OTRS_VERIFY_SSL",
        True,
    )

    print("=" * 70)
    print("Teste de conectividade OTRS Generic Interface")
    print("=" * 70)
    print(
        f"OTRS_BASE_URL   : "
        f"{base_url or '(NÃO DEFINIDA)'}"
    )
    print(
        f"OTRS_USERNAME   : "
        f"{username or '(NÃO DEFINIDA)'}"
    )
    print(
        f"OTRS_PASSWORD   : "
        f"{'(definida)' if password else '(NÃO DEFINIDA)'}"
    )
    print(
        f"OTRS_VERIFY_SSL : {verify_ssl}"
    )
    print("-" * 70)

    missing = [
        name
        for name, value in (
            ("OTRS_BASE_URL", base_url),
            ("OTRS_USERNAME", username),
            ("OTRS_PASSWORD", password),
        )
        if not value
    ]

    if missing:
        print(
            "[ERRO] Variáveis obrigatórias faltando: "
            f"{', '.join(missing)}"
        )
        sys.exit(1)

    if not base_url.lower().startswith(
        ("http://", "https://")
    ):
        print(
            "[ERRO] OTRS_BASE_URL deve começar com "
            "http:// ou https://."
        )
        sys.exit(1)

    if not verify_ssl:
        print(
            "[AVISO] Verificação do certificado SSL desativada."
        )
        print(
            "        Utilize essa configuração somente em testes "
            "ou com certificado autoassinado conhecido."
        )
        print("-" * 70)

    # ==============================================================
    # Passo 1: SessionCreate
    # ==============================================================

    session_url = f"{base_url}/SessionCreate"

    print(
        f"[1/2] Chamando SessionCreate em:\n"
        f"      {session_url}"
    )

    session_payload = {
        "CustomerUserLogin": username,
        "Password": password,
    }

    status, body, error = post_json(
        session_url,
        session_payload,
        verify_ssl,
    )

    if error:
        print(f"[ERRO] {error}")
        print(
            "       Verifique a URL, DNS, firewall, porta 443 "
            "e o certificado TLS."
        )
        sys.exit(1)

    print(f"       HTTP status: {status}")

    if status != 200:
        print(
            f"[ERRO] SessionCreate retornou HTTP {status}."
        )
        print(
            f"       Corpo da resposta: {body[:1000]}"
        )
        print(
            "       Verifique o nome do Web Service, a rota "
            "SessionCreate e o método POST."
        )
        sys.exit(1)

    session_data = parse_json_response(
        body,
        "SessionCreate",
    )

    if session_data is None:
        sys.exit(1)

    if print_otrs_error(
        "SessionCreate",
        session_data,
    ):
        sys.exit(1)

    session_id = session_data.get("SessionID")

    if (
        not isinstance(session_id, str)
        or not session_id.strip()
    ):
        print(
            "[ERRO] SessionCreate retornou HTTP 200, "
            "mas sem uma SessionID válida."
        )
        print(
            f"       Corpo da resposta: {body[:500]}"
        )
        sys.exit(1)

    session_id = session_id.strip()

    print(
        "       [OK] SessionID obtida "
        "(autenticação válida)."
    )
    print("-" * 70)

    # ==============================================================
    # Passo 2: TicketSearch usando a SessionID
    # ==============================================================

    search_url = f"{base_url}/TicketSearch"

    print(
        f"[2/2] Chamando TicketSearch em:\n"
        f"      {search_url}"
    )

    search_payload = {
        "SessionID": session_id,
        "Limit": 1,
    }

    status, body, error = post_json(
        search_url,
        search_payload,
        verify_ssl,
    )

    if error:
        print(f"[ERRO] {error}")
        sys.exit(1)

    print(f"       HTTP status: {status}")

    if status != 200:
        print(
            f"[ERRO] TicketSearch retornou HTTP {status}."
        )
        print(
            f"       Corpo da resposta: {body[:1000]}"
        )
        print(
            "       O SessionCreate funcionou. Verifique a rota "
            "TicketSearch e se o método POST está permitido."
        )
        sys.exit(2)

    search_data = parse_json_response(
        body,
        "TicketSearch",
    )

    if search_data is None:
        sys.exit(2)

    if print_otrs_error(
        "TicketSearch",
        search_data,
    ):
        sys.exit(2)

    ticket_ids = search_data.get("TicketID") or []

    if isinstance(ticket_ids, list):
        ticket_count = len(ticket_ids)
    else:
        ticket_count = 1

    print(
        "       [OK] TicketSearch respondeu corretamente "
        f"(TicketID retornados: {ticket_count})."
    )
    print("-" * 70)
    print(
        "RESULTADO: credenciais e Web Service "
        "validados com sucesso."
    )
    print(
        "A SessionID criada foi aceita pela operação TicketSearch."
    )


if __name__ == "__main__":
    main()