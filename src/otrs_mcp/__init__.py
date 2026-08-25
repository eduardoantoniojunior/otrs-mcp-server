"""OTRS MCP Server.

Servidor MCP (Model Context Protocol) para integracao com o OTRS.
Permite que LLMs criem, consultem, busquem e atualizem tickets.
Suporta autenticacao via API key (agentes) e JWT (admin panel).
"""

__version__ = "0.2.0"

from otrs_mcp.activity import get_activity, get_summary, record_tool_call
from otrs_mcp.auth import create_access_token, get_api_key_identity, get_current_admin
from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.database import create_api_key, init_db, verify_api_key
from otrs_mcp.tools import mcp

__all__ = [
    "OTRSClient",
    "OTRSConfig",
    "mcp",
    "record_tool_call",
    "get_activity",
    "get_summary",
    "create_access_token",
    "get_api_key_identity",
    "get_current_admin",
    "init_db",
    "create_api_key",
    "verify_api_key",
]
