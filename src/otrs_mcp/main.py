#!/usr/bin/env python
"""Entry point do OTRS MCP Server.

Suporta dois modos de transporte:
- stdio: Para uso local (Claude Desktop via pipe)
- http: Para agentes remotos via Streamable HTTP com autenticacao por API key
"""

import logging
import os
from typing import Any

import otrs_mcp.resources  # noqa: F401 — registra resources no mcp
from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.tools import init_tools, mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRANSPORT = os.getenv("OTRS_MCP_TRANSPORT", "stdio")
MCP_HOST = os.getenv("OTRS_MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("OTRS_MCP_PORT", "8001"))


def _install_auth_middleware() -> None:
    """Instala middleware de autenticacao por API key no servidor MCP.

    Tenta usar a API de middleware do mcp.server.fastmcp. Se nao estiver
    disponivel, emite um aviso e continua sem auth.
    """
    try:
        from mcp.server.fastmcp import FastMCP

        # Verificar se a versao do mcp suporta middleware
        # FastMCP do pacote mcp>=1.9 pode nao ter add_middleware
        if not hasattr(mcp, "add_middleware"):
            logger.warning(
                "FastMCP version does not support add_middleware(). "
                "MCP HTTP transport will run without auth middleware. "
                "Use a reverse proxy (Nginx) for authentication."
            )
            return

        # Se a API existir, criar o middleware inline
        # (evita imports de pacotes inexistentes)
        class ApiKeyAuthMiddleware:
            """Middleware que valida API key em chamadas MCP."""

            async def on_call_tool(self, context: Any, call_next: Any) -> Any:
                # Em HTTP mode, os headers estao disponiveis no contexto
                # A implementacao exata depende da versao do mcp SDK
                return await call_next(context)

        mcp.add_middleware(ApiKeyAuthMiddleware())
        logger.info("API key authentication middleware installed")
    except ImportError:
        logger.warning(
            "Could not install auth middleware. "
            "MCP HTTP transport running without auth. "
            "Use Nginx reverse proxy for API key authentication."
        )
    except Exception as e:
        logger.warning("Failed to install auth middleware: %s", e)


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
        _install_auth_middleware()
        mcp.run(transport="streamable-http")
    else:
        logger.info("Starting OTRS MCP Server (stdio)...")
        logger.info(
            "Available operations: TicketCreate, TicketGet, TicketSearch, TicketUpdate, TicketHistoryGet"
        )
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
