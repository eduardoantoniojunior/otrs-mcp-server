#!/usr/bin/env python
"""Entry point do OTRS MCP Server."""

import logging
import sys

from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.resources import mcp  # noqa: F401 — registra resources
from otrs_mcp.tools import init_tools, mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    logger.info("Starting OTRS MCP Server...")
    logger.info(
        "Available operations: TicketCreate, TicketGet, TicketSearch, TicketUpdate, TicketHistoryGet"
    )

    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
