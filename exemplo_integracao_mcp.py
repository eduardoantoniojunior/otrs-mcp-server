"""
Exemplo de integração com o OTRS MCP Server.

Este arquivo mostra como conectar uma aplicação de agente de IA
ao OTRS MCP Server via protocolo MCP.

Suporta dois modos de conexão:
  - stdio: Para uso local (o servidor MCP roda como subprocess)
  - http: Para uso remoto (o servidor MCP roda na AWS via Docker)

Requisitos:
    pip install mcp httpx

Uso:
    1. Via processo local (stdio):
       python exemplo_integracao_mcp.py

    2. Via HTTP remoto (apontando para a AWS):
       Altere MODO_CONEXAO = "http" e configure OTRS_REMOTE_URL e OTRS_API_KEY.
       python exemplo_integracao_mcp.py

    3. Configuração no seu agente (ex: Claude Desktop, Cursor, etc.):

       Para modo STDIO (local):
       {
           "mcpServers": {
               "otrs": {
                   "command": "uv",
                   "args": ["run", "python", "-m", "otrs_mcp.main"],
                   "cwd": "/caminho/para/otrs-mcp-server",
                   "env": {
                       "OTRS_BASE_URL": "https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/MCPConnector",
                       "OTRS_USERNAME": "seu-usuario",
                       "OTRS_PASSWORD": "sua-senha",
                       "OTRS_VERIFY_SSL": "true",
                       "OTRS_DEFAULT_QUEUE": "Suporte::Zabbix",
                       "OTRS_MCP_TRANSPORT": "stdio"
                   }
               }
           }
       }

       Para modo HTTP (remoto):
       {
           "mcpServers": {
               "otrs": {
                   "url": "https://seu-dominio-ou-ip:8081/mcp",
                   "headers": {
                       "Authorization": "Bearer sk-otrs-sua-api-key-aqui"
                   }
               }
           }
       }
"""

import asyncio
import contextlib
import json
import os
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client


# =============================================================================
# Configuração — ajuste conforme seu ambiente
# =============================================================================

# MODO DE CONEXÃO: "stdio" (local) ou "http" (remoto na AWS)
MODO_CONEXAO = "stdio"

# ---------- Configuração para modo STDIO (local) ----------

# Caminho para o projeto otrs-mcp-server
OTRS_MCP_PROJECT_DIR = r"C:\caminho\para\otrs-mcp-server"

# Variáveis de ambiente do OTRS (serão passadas ao subprocess)
OTRS_ENV = {
    "OTRS_BASE_URL": "https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/MCPConnector",
    "OTRS_USERNAME": "seu-usuario",
    "OTRS_PASSWORD": "sua-senha",
    "OTRS_VERIFY_SSL": "true",
    "OTRS_TIMEOUT": "30",
    "OTRS_DEFAULT_QUEUE": "Suporte::Zabbix",
    "OTRS_DEFAULT_PRIORITY": "3 normal",
    "OTRS_DEFAULT_TYPE": "",
    "OTRS_MCP_TRANSPORT": "stdio",
}

# ---------- Configuração para modo HTTP (remoto) ----------

# URL do MCP Server na AWS (porta 8081 = Caddy reverse proxy)
OTRS_REMOTE_URL = "https://seu-dominio-ou-ip:8081/mcp"

# API Key gerada no painel web (API Keys)
OTRS_API_KEY = "sk-otrs-sua-api-key-aqui"


# =============================================================================
# Conexão com o MCP Server
# =============================================================================

def get_stdio_params() -> StdioServerParameters:
    """Configura os parâmetros para iniciar o MCP server localmente (stdio)."""
    env = {**os.environ, **OTRS_ENV}

    return StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "otrs_mcp.main"],
        cwd=OTRS_MCP_PROJECT_DIR,
        env=env,
    )


@contextlib.asynccontextmanager
async def conectar_mcp():
    """Gerencia a conexão baseada no modo escolhido."""
    if MODO_CONEXAO == "stdio":
        print("🔌 Conectando ao OTRS MCP Server via STDIO (Local)...")
        server_params = get_stdio_params()
        async with stdio_client(server_params) as (read_stream, write_stream):
            yield read_stream, write_stream

    elif MODO_CONEXAO == "http":
        print(f"🌐 Conectando ao OTRS MCP Server via HTTP (Remoto) em {OTRS_REMOTE_URL}...")
        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {OTRS_API_KEY}"},
            verify=False,  # Use True em produção com SSL válido
        )
        async with streamable_http_client(OTRS_REMOTE_URL, http_client=http_client) as streams:
            # streamable_http_client retorna (read_stream, write_stream, session_id_callback)
            yield streams[0], streams[1]

    else:
        raise ValueError(f"Modo de conexão desconhecido: {MODO_CONEXAO}")


# =============================================================================
# Exemplos de uso das Tools MCP
# =============================================================================

async def listar_tools(session: ClientSession) -> None:
    """Lista todas as tools disponíveis no MCP server."""
    print("\n" + "=" * 60)
    print("TOOLS DISPONÍVEIS")
    print("=" * 60)

    tools = await session.list_tools()
    for tool in tools.tools:
        print(f"\n  📌 {tool.name}")
        print(f"     {tool.description}")
        if tool.inputSchema and "properties" in tool.inputSchema:
            params = tool.inputSchema["properties"]
            required = tool.inputSchema.get("required", [])
            for param_name, param_info in params.items():
                req = " (obrigatório)" if param_name in required else ""
                param_type = param_info.get("type", "any")
                print(f"     - {param_name}: {param_type}{req}")


async def listar_resources(session: ClientSession) -> None:
    """Lista todos os resources disponíveis no MCP server."""
    print("\n" + "=" * 60)
    print("RESOURCES DISPONÍVEIS")
    print("=" * 60)

    resources = await session.list_resources()
    for resource in resources.resources:
        print(f"\n  📂 {resource.uri}")
        if resource.description:
            print(f"     {resource.description}")


async def criar_ticket(session: ClientSession) -> str | None:
    """Exemplo: criar um novo ticket no OTRS.

    Parâmetros disponíveis:
        - title (str, obrigatório): Título/assunto do ticket
        - body (str, obrigatório): Corpo/descrição do ticket
        - queue (str, opcional): Fila do ticket (ex: "Suporte::Zabbix")
        - priority (str, opcional): Prioridade (ex: "3 normal", "4 high")
        - state (str, opcional): Estado (ex: "new", "open")
        - customer_user (str, opcional): Email/login do cliente
        - ticket_type (str, opcional): Tipo do ticket (ex: "Event")
    """
    print("\n" + "=" * 60)
    print("CRIANDO TICKET")
    print("=" * 60)

    result = await session.call_tool(
        "create_ticket",
        arguments={
            "title": "Teste via MCP - Agente de IA",
            "body": "Este ticket foi criado automaticamente por um agente de IA via MCP.",
            "queue": "Suporte::Zabbix",
            "priority": "3 normal",
            "state": "new",
            # customer_user é opcional; se omitido, usa o usuário do .env
            # ticket_type é opcional; se omitido e OTRS exigir, usa o default do .env
        },
    )

    for content in result.content:
        if hasattr(content, "text"):
            data = json.loads(content.text)
            ticket_id = data.get("TicketID")
            web_url = data.get("WebURL")
            print(f"  ✅ Ticket criado: #{ticket_id}")
            print(f"     URL: {web_url}")
            return str(ticket_id)

    return None


async def consultar_ticket(session: ClientSession, ticket_id: str) -> None:
    """Exemplo: consultar detalhes de um ticket.

    Parâmetros disponíveis:
        - ticket_id (str, obrigatório): ID do ticket
        - include_dynamic_fields (bool, opcional): Incluir campos dinâmicos
        - include_extended_data (bool, opcional): Incluir dados estendidos
    """
    print("\n" + "=" * 60)
    print(f"CONSULTANDO TICKET #{ticket_id}")
    print("=" * 60)

    result = await session.call_tool(
        "get_ticket",
        arguments={
            "ticket_id": ticket_id,
            "include_dynamic_fields": True,
            "include_extended_data": True,
        },
    )

    for content in result.content:
        if hasattr(content, "text"):
            data = json.loads(content.text)
            ticket = data.get("Ticket", [{}])
            if isinstance(ticket, list) and ticket:
                t = ticket[0]
                print(f"  ID:          {t.get('TicketID')}")
                print(f"  Título:      {t.get('Title')}")
                print(f"  Fila:        {t.get('Queue')}")
                print(f"  Estado:      {t.get('State')}")
                print(f"  Prioridade:  {t.get('Priority')}")
                print(f"  Tipo:        {t.get('Type')}")
                print(f"  Responsável: {t.get('Owner')}")
                print(f"  Criado em:   {t.get('Created')}")
            print(f"  Web URL:     {data.get('WebURL')}")


async def buscar_tickets(session: ClientSession) -> None:
    """Exemplo: buscar tickets com filtros.

    Parâmetros disponíveis:
        - customer_user (str, opcional): Login do cliente
        - customer_id (str, opcional): ID da empresa/organização do cliente
        - queue (str, opcional): Filtrar por fila
        - state (str, opcional): Filtrar por estado
        - priority (str, opcional): Filtrar por prioridade
        - title (str, opcional): Buscar no título (use * como curinga, ex: "*Moriah*")
        - limit (int, opcional): Limite de resultados (padrão: 50)
        - sort_by (str, opcional): Campo para ordenar (padrão: "Age")
        - order_by (str, opcional): Direção da ordenação (padrão: "Down")
    """
    print("\n" + "=" * 60)
    print("BUSCANDO TICKETS")
    print("=" * 60)

    # Exemplo 1: Buscar tickets novos
    print("\n  --- Tickets novos ---")
    result = await session.call_tool(
        "search_tickets",
        arguments={
            "state": "new",
            "limit": 10,
            "sort_by": "Age",
            "order_by": "Down",
        },
    )

    for content in result.content:
        if hasattr(content, "text"):
            data = json.loads(content.text)
            ticket_ids = data.get("TicketID", [])
            print(f"  Encontrados: {len(ticket_ids)} tickets")
            for tid in ticket_ids[:5]:
                print(f"    - Ticket #{tid}")
            if len(ticket_ids) > 5:
                print(f"    ... e mais {len(ticket_ids) - 5}")

    # Exemplo 2: Buscar por título com curinga
    print("\n  --- Busca por título ---")
    result = await session.call_tool(
        "search_tickets",
        arguments={
            "title": "*Moriah*",
            "limit": 10,
        },
    )

    for content in result.content:
        if hasattr(content, "text"):
            data = json.loads(content.text)
            ticket_ids = data.get("TicketID", [])
            print(f"  Encontrados com '*Moriah*': {len(ticket_ids)} tickets")
            for tid in ticket_ids:
                print(f"    - Ticket #{tid}")

    # Exemplo 3: Buscar por empresa (customer_id)
    print("\n  --- Busca por empresa ---")
    result = await session.call_tool(
        "search_tickets",
        arguments={
            "customer_id": "NomeDaEmpresa",
            "limit": 10,
        },
    )

    for content in result.content:
        if hasattr(content, "text"):
            data = json.loads(content.text)
            ticket_ids = data.get("TicketID", [])
            print(f"  Encontrados da empresa: {len(ticket_ids)} tickets")
            for tid in ticket_ids:
                print(f"    - Ticket #{tid}")


# =============================================================================
# Execução principal
# =============================================================================

async def main() -> None:
    """Conecta ao MCP server e executa os exemplos."""
    async with conectar_mcp() as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Inicializa a sessão MCP
            await session.initialize()
            print("✅ Conectado ao OTRS MCP Server!\n")

            # 1. Listar tools e resources
            await listar_tools(session)
            await listar_resources(session)

            # 2. Buscar tickets existentes
            await buscar_tickets(session)

            # Os próximos exemplos estão comentados para evitar criar
            # tickets reais por acidente. Descomente para testar.

            # 3. Criar um novo ticket
            # ticket_id = await criar_ticket(session)
            # if ticket_id:
            #     # 4. Consultar o ticket criado
            #     await consultar_ticket(session, ticket_id)

            # 5. Consultar um ticket existente pelo ID
            # await consultar_ticket(session, "93173998")

            print("\n" + "=" * 60)
            print("✅ Exemplos finalizados!")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
