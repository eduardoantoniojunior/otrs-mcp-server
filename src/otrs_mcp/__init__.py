"""OTRS MCP Server.

Servidor MCP (Model Context Protocol) para integracao com o OTRS.
Permite que LLMs criem, consultem, busquem e atualizem tickets.
"""

__version__ = "0.1.0"

from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.tools import mcp

__all__ = ["OTRSClient", "OTRSConfig", "mcp"]
