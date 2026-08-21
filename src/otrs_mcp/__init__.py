"""OTRS MCP Server.

Servidor MCP (Model Context Protocol) para integracao com o OTRS.
Permite que LLMs criem, consultem, busquem e atualizem tickets.
"""

__version__ = "0.1.0"

from otrs_mcp.activity import get_activity, get_summary, record_tool_call
from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.tools import mcp

__all__ = [
    "OTRSClient",
    "OTRSConfig",
    "mcp",
    "record_tool_call",
    "get_activity",
    "get_summary",
]
