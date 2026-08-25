"""
Exemplo de integração com o OTRS MCP Server.

Este arquivo mostra como conectar uma aplicação de agente de IA
ao OTRS MCP Server via protocolo MCP (stdio).

Requisitos:
    pip install mcp

Uso:
    1. Via processo local:
       python exemplo_integracao_mcp.py

    2. Configuração no seu agente (ex: Claude Desktop):
       Adicione ao mcp_config.json:
       {
           "mcpServers": {
               "otrs": {
                   "command": "uv",
                   "args": ["run", "python", "-m", "otrs_mcp.main"],
                   "cwd": "C:\\caminho\\para\\otrs-mcp-server",
                   "env": {
                       "OTRS_BASE_URL": "https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/TestInterface",
                       "OTRS_USERNAME": "seu-usuario",
                       "OTRS_PASSWORD": "sua-senha",
                       "OTRS_VERIFY_SSL": "false"
                   }
               }
           }
       }
"""

import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# =============================================================================
# Configuração — ajuste conforme seu ambiente
# =============================================================================

# Caminho para o projeto otrs-mcp-server
OTRS_MCP_PROJECT_DIR = r"C:\Users\ejunior\OneDrive - beonup.com.br\Trabalho\BeOnUp\Projeto Vigilante\Servidor OTRS MCP\otrs-mcp-server"

# Variáveis de ambiente do OTRS (serão passadas ao subprocess)
OTRS_ENV = {
    "OTRS_BASE_URL": "https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/TestInterface",
    "OTRS_USERNAME": "seu-usuario",
    "OTRS_PASSWORD": "sua-senha",
    "OTRS_VERIFY_SSL": "false",
    "OTRS_TIMEOUT": "30",
    "OTRS_DEFAULT_QUEUE": "Raw",
    "OTRS_DEFAULT_PRIORITY": "3 normal",
}


# =============================================================================
# Conexão com o MCP Server
# =============================================================================

# ESCOLHA O MODO DE CONEXÃO: "stdio" (local) ou "http" (remoto na AWS)
MODO_CONEXAO = "stdio" 

# Configurações para modo "http" (remoto)
OTRS_REMOTE_URL = "https://seu-dominio-ou-ip/mcp"
OTRS_API_KEY = "sk-otrs-sua-api-key-aqui"

def get_stdio_params() -> StdioServerParameters:
    """Configura os parâmetros para iniciar o MCP server localmente (stdio)."""
    env = {**os.environ, **OTRS_ENV}

    return StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "otrs_mcp.main"],
        cwd=OTRS_MCP_PROJECT_DIR,
        env=env,
    )

import contextlib
import httpx
from mcp.client.streamable_http import streamable_http_client

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
            verify=False # Desative em prod ou se usar IP direto sem SSL válido
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
    """Exemplo: criar um novo ticket no OTRS."""
    print("\n" + "=" * 60)
    print("CRIANDO TICKET")
    print("=" * 60)

    result = await session.call_tool(
        "create_ticket",
        arguments={
            "title": "Teste via MCP - Agente de IA",
            "body": "Este ticket foi criado automaticamente por um agente de IA via MCP.",
            "queue": "Raw",
            "priority": "3 normal",
            "state": "new",
            "customer_user": "agente@exemplo.com",
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
    """Exemplo: consultar detalhes de um ticket."""
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
                print(f"  Responsável: {t.get('Owner')}")
                print(f"  Criado em:   {t.get('Created')}")
            print(f"  Web URL:     {data.get('WebURL')}")


async def buscar_tickets(session: ClientSession) -> None:
    """Exemplo: buscar tickets com filtros."""
    print("\n" + "=" * 60)
    print("BUSCANDO TICKETS")
    print("=" * 60)

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
            #     # 4. Consultar o ticket
            #     await consultar_ticket(session, ticket_id)

            print("\n" + "=" * 60)
            print("✅ Exemplos finalizados!")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
