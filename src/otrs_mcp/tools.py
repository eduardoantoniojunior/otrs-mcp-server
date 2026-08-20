"""Tools MCP para o OTRS."""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.constants import VALID_PRIORITIES, VALID_QUEUES
from otrs_mcp.exceptions import OTRSValidationError

logger = logging.getLogger(__name__)

mcp = FastMCP("OTRS API MCP")

_client: OTRSClient | None = None
_config: OTRSConfig | None = None


def init_tools(config: OTRSConfig, client: OTRSClient) -> None:
    """Inicializa as tools com config e client compartilhados."""
    global _client, _config
    _client = client
    _config = config


def _get_client() -> OTRSClient:
    if _client is None:
        raise RuntimeError("Tools nao inicializadas. Chame init_tools() primeiro.")
    return _client


def _get_config() -> OTRSConfig:
    if _config is None:
        raise RuntimeError("Tools nao inicializadas. Chame init_tools() primeiro.")
    return _config


@mcp.tool(description="Create a new ticket in OTRS")
async def create_ticket(
    title: str,
    body: str,
    queue: str | None = None,
    priority: str | None = None,
    state: str | None = None,
    customer_user: str | None = None,
    ticket_type: str | None = None,
) -> dict[str, Any]:
    client = _get_client()
    config = _get_config()

    resolved_queue = queue if queue in VALID_QUEUES else config.default_queue
    resolved_priority = priority or config.default_priority

    if priority and priority.lower() not in {p.lower() for p in VALID_PRIORITIES}:
        raise OTRSValidationError(
            f"Prioridade invalida: '{priority}'. Valores validos: {', '.join(sorted(VALID_PRIORITIES))}"
        )

    return await client.create_ticket(
        title=title,
        body=body,
        queue=resolved_queue,
        priority=resolved_priority,
        state=state,
        customer_user=customer_user,
        ticket_type=ticket_type,
    )


@mcp.tool(description="Get ticket details from OTRS")
async def get_ticket(
    ticket_id: str,
    include_dynamic_fields: bool = True,
    include_extended_data: bool = True,
) -> dict[str, Any]:
    client = _get_client()
    return await client.get_ticket(
        ticket_id=ticket_id,
        include_dynamic_fields=include_dynamic_fields,
        include_extended_data=include_extended_data,
    )


@mcp.tool(description="Search for tickets in OTRS")
async def search_tickets(
    customer_user: str | None = None,
    queue: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    title: str | None = None,
    limit: int = 50,
    sort_by: str = "Age",
    order_by: str = "Down",
) -> dict[str, Any]:
    client = _get_client()
    return await client.search_tickets(
        customer_user=customer_user,
        queue=queue,
        state=state,
        priority=priority,
        title=title,
        limit=limit,
        sort_by=sort_by,
        order_by=order_by,
    )


@mcp.tool(description="Update an existing ticket in OTRS")
async def update_ticket(
    ticket_id: str,
    title: str | None = None,
    queue: str | None = None,
    priority: str | None = None,
    state: str | None = None,
    customer_user: str | None = None,
    owner: str | None = None,
) -> dict[str, Any]:
    client = _get_client()

    if priority and priority.lower() not in {p.lower() for p in VALID_PRIORITIES}:
        raise OTRSValidationError(
            f"Prioridade invalida: '{priority}'. Valores validos: {', '.join(sorted(VALID_PRIORITIES))}"
        )

    return await client.update_ticket(
        ticket_id=ticket_id,
        title=title,
        queue=queue,
        priority=priority,
        state=state,
        customer_user=customer_user,
        owner=owner,
    )


@mcp.tool(description="Get ticket history from OTRS")
async def get_ticket_history(ticket_id: str) -> dict[str, Any]:
    client = _get_client()
    return await client.get_ticket_history(ticket_id=ticket_id)
