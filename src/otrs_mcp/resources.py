"""Resources MCP para o OTRS."""

import json
import logging

from otrs_mcp.tools import mcp, _get_client

logger = logging.getLogger(__name__)


@mcp.resource("otrs://ticket/{ticket_id}")
async def ticket_resource(ticket_id: str) -> str:
    """Retorna dados do ticket com links para a interface web."""
    try:
        client = _get_client()
        ticket = await client.get_ticket(ticket_id=ticket_id)
        return json.dumps(ticket, indent=2)
    except Exception as e:
        logger.error("Erro ao obter ticket %s: %s", ticket_id, e)
        return f"Error retrieving ticket: {e}"


@mcp.resource("otrs://ticket/{ticket_id}/history")
async def ticket_history_resource(ticket_id: str) -> str:
    """Retorna historico do ticket com links para a interface web."""
    try:
        client = _get_client()
        history = await client.get_ticket_history(ticket_id=ticket_id)
        return json.dumps(history, indent=2)
    except Exception as e:
        logger.error("Erro ao obter historico do ticket %s: %s", ticket_id, e)
        return f"Error retrieving ticket history: {e}"


@mcp.resource("otrs://search/tickets")
async def search_tickets_resource() -> str:
    """Retorna tickets recentes com links para a interface web."""
    try:
        client = _get_client()
        tickets = await client.search_tickets(limit=20)
        return json.dumps(tickets, indent=2)
    except Exception as e:
        logger.error("Erro ao buscar tickets: %s", e)
        return f"Error searching tickets: {e}"
