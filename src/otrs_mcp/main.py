#!/usr/bin/env python
"""Entry point do OTRS MCP Server.

Suporta dois modos de transporte:
- stdio: Para uso local (Claude Desktop via pipe)
- http: Para agentes remotos via Streamable HTTP com autenticacao por API key
"""

import logging
import os

import otrs_mcp.resources  # noqa: F401 — registra resources no mcp
from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.tools import init_tools, mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRANSPORT = os.getenv("OTRS_MCP_TRANSPORT", "stdio")
MCP_HOST = os.getenv("OTRS_MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("OTRS_MCP_PORT", "8001"))


def _init_database() -> None:
    """Garante que o schema existe antes de validar API keys.

    No transporte HTTP o servidor consulta a tabela `api_keys` a cada
    requisicao. Quando o MCP roda em container separado da API, o banco pode
    ainda nao ter sido inicializado.
    """
    from otrs_mcp.database import init_db

    try:
        init_db()
    except Exception as e:
        logger.warning("Nao foi possivel inicializar o banco de dados: %s", e)


def run_server() -> None:
    config = OTRSConfig()
    client = OTRSClient(config)
    init_tools(config, client)

    logger.info("OTRS MCP Server Configuration:")
    logger.info("  Base URL: %s", config.base_url)
    logger.info("  Username: [configured]")
    logger.info("  SSL Verify: %s", config.verify_ssl)
    logger.info("  Timeout: %ds", config.timeout)
    logger.info("  Default Queue: %s", config.default_queue)
    logger.info("  Default State: %s", config.default_state)
    logger.info("  Default Priority: %s", config.default_priority)
    logger.info("  Default Type: %s", config.default_type)
    logger.info("  Transport: %s", TRANSPORT)

    if TRANSPORT == "http":
        logger.info(
            "Starting OTRS MCP Server (Streamable HTTP on %s:%d)...", MCP_HOST, MCP_PORT
        )
        _init_database()
        logger.info(
            "  Auth: API key obrigatoria em 'Authorization: Bearer sk-otrs-...'"
        )
        mcp.run(transport="streamable-http")
    else:
        logger.info("Starting OTRS MCP Server (stdio)...")
        logger.info(
            "Available operations: TicketCreate, TicketGet, TicketSearch, TicketUpdate, TicketHistoryGet"
        )
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
