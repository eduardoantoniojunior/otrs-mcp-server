#!/usr/bin/env python
import logging
import sys

from otrs_mcp.server import config, mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_server() -> None:
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
