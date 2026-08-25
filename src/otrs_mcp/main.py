#!/usr/bin/env python
"""Entry point do OTRS MCP Server.

Suporta dois modos de transporte:
- stdio: Para uso local (Claude Desktop via pipe)
- http: Para agentes remotos via Streamable HTTP com autenticacao por API key
"""

import logging
import os
import sys
from typing import Any

from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
import otrs_mcp.resources  # noqa: F401 — registra resources no mcp
from otrs_mcp.tools import init_tools, mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TRANSPORT = os.getenv("OTRS_MCP_TRANSPORT", "stdio")
MCP_HOST = os.getenv("OTRS_MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("OTRS_MCP_PORT", "8001"))


def _verify_api_key_middleware(api_key: str) -> bool:
    """Verifica se uma API key e valida."""
    from otrs_mcp.database import init_db, verify_api_key
    init_db()
    identity = verify_api_key(api_key)
    return identity is not None


def run_server() -> None:
    config = OTRSConfig()
    client = OTRSClient(config)
    init_tools(config, client)

    logger.info("OTRS MCP Server Configuration:")
    logger.info("  Base URL: %s", config.base_url)
    logger.info("  Username: %s", config.username)
    logger.info("  SSL Verify: %s", config.verify_ssl)
    logger.info("  Timeout: %ds", config.timeout)
    logger.info("  Default Queue: %s", config.default_queue)
    logger.info("  Default State: %s", config.default_state)
    logger.info("  Default Priority: %s", config.default_priority)
    logger.info("  Default Type: %s", config.default_type)
    logger.info("  Transport: %s", TRANSPORT)

    if TRANSPORT == "http":
        logger.info("Starting OTRS MCP Server (Streamable HTTP on %s:%d)...", MCP_HOST, MCP_PORT)
        logger.info("API key authentication required via X-API-Key or Authorization: Bearer header")

        # Para Streamable HTTP, precisamos configurar o servidor com auth
        # FastMCP suporta auth via middleware
        try:
            from fastmcp.server.middleware import Middleware, MiddlewareContext
            from fastmcp.server.dependencies import get_http_headers
            from fastmcp.exceptions import ToolError

            class ApiKeyAuthMiddleware(Middleware):
                """Middleware que valida API key em todas as chamadas de tool."""

                async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
                    headers = get_http_headers()
                    api_key = headers.get("x-api-key") or None

                    if not api_key and headers.get("authorization", "").startswith("Bearer "):
                        api_key = headers["authorization"].removeprefix("Bearer ").strip()

                    if not api_key:
                        raise ToolError("API key necessaria (header X-API-Key ou Authorization: Bearer)")

                    if not _verify_api_key_middleware(api_key):
                        raise ToolError("API key invalida, inativa ou expirada")

                    return await call_next(context)

            mcp.add_middleware(ApiKeyAuthMiddleware())
            logger.info("API key authentication middleware installed")
        except ImportError:
            logger.warning("FastMCP middleware not available, running without auth middleware")

        mcp.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT)
    else:
        logger.info("Starting OTRS MCP Server (stdio)...")
        logger.info(
            "Available operations: TicketCreate, TicketGet, TicketSearch, TicketUpdate, TicketHistoryGet"
        )
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
