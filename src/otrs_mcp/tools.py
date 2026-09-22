"""Tools MCP para o OTRS."""

import logging
import os
import time
from typing import Any

from mcp.server.fastmcp import FastMCP

from otrs_mcp.activity import record_tool_call
from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.constants import VALID_ARTICLE_ORDERS, VALID_PRIORITIES
from otrs_mcp.exceptions import OTRSValidationError
from otrs_mcp.mcp_auth import (
    ApiKeyVerifier,
    auth_enabled,
    build_auth_settings,
    require_scope,
)
from otrs_mcp.validation import validate_ticket_id

logger = logging.getLogger(__name__)

MCP_HOST = os.getenv("OTRS_MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("OTRS_MCP_PORT", "8001"))

# No transporte HTTP o servidor exige uma API key valida em cada requisicao.
# O FastMCP obriga informar token_verifier e auth em conjunto.
if auth_enabled():
    mcp = FastMCP(
        "OTRS API MCP",
        host=MCP_HOST,
        port=MCP_PORT,
        token_verifier=ApiKeyVerifier(),
        auth=build_auth_settings(),
    )
    logger.info("MCP: autenticacao por API key ativa (transporte http)")
else:
    mcp = FastMCP("OTRS API MCP", host=MCP_HOST, port=MCP_PORT)

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


def _extract_ticket_id(result: Any) -> str | None:
    if isinstance(result, dict):
        return str(result.get("TicketID", "")) or None
    return None


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
    require_scope("write")
    client = _get_client()
    config = _get_config()

    resolved_queue = queue if queue else config.default_queue
    resolved_priority = priority or config.default_priority

    if priority and priority.lower() not in {p.lower() for p in VALID_PRIORITIES}:
        record_tool_call(
            tool="create_ticket",
            status="error",
            duration_ms=0,
            params={"title": title, "queue": queue, "priority": priority},
            error=f"Prioridade invalida: {priority}",
        )
        raise OTRSValidationError(
            f"Prioridade invalida: '{priority}'. Valores validos: {', '.join(sorted(VALID_PRIORITIES))}"
        )

    start = time.monotonic()
    try:
        result = await client.create_ticket(
            title=title,
            body=body,
            queue=resolved_queue,
            priority=resolved_priority,
            state=state,
            customer_user=customer_user,
            ticket_type=ticket_type,
        )
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="create_ticket",
            status="success",
            duration_ms=elapsed,
            params={
                "title": title,
                "queue": resolved_queue,
                "priority": resolved_priority,
            },
            ticket_id=_extract_ticket_id(result),
        )
        return result
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="create_ticket",
            status="error",
            duration_ms=elapsed,
            params={
                "title": title,
                "queue": resolved_queue,
                "priority": resolved_priority,
            },
            error=str(e),
        )
        raise


@mcp.tool(
    description=(
        "Get ticket details from OTRS. Returns metadata (Title, Queue, State, "
        "Priority, Customer, dates), plus WebURL and HistoryWebURL. When "
        "include_articles=True, also returns 'Articles' (list) with the body "
        "of each article (customer messages and agent replies)."
    )
)
async def get_ticket(
    ticket_id: str,
    include_dynamic_fields: bool = True,
    include_extended_data: bool = True,
    include_articles: bool = False,
    article_limit: int | None = None,
    article_order: str = "desc",
    article_sender_type: str | None = None,
) -> dict[str, Any]:
    require_scope("read")
    validate_ticket_id(ticket_id)
    if article_order.lower() not in VALID_ARTICLE_ORDERS:
        raise OTRSValidationError(
            f"article_order invalido: '{article_order}'. "
            f"Valores validos: {', '.join(sorted(VALID_ARTICLE_ORDERS))}"
        )
    client = _get_client()
    start = time.monotonic()
    try:
        result = await client.get_ticket(
            ticket_id=ticket_id,
            include_dynamic_fields=include_dynamic_fields,
            include_extended_data=include_extended_data,
            include_articles=include_articles,
            article_limit=article_limit,
            article_order=article_order,
            article_sender_type=article_sender_type,
        )
        elapsed = (time.monotonic() - start) * 1000
        # Nao gravamos o corpo dos artigos na atividade: params contem apenas
        # ids e flags, o retorno com o Body fica so no canal MCP.
        record_tool_call(
            tool="get_ticket",
            status="success",
            duration_ms=elapsed,
            params={
                "ticket_id": ticket_id,
                "include_articles": include_articles,
                "article_limit": article_limit,
                "article_order": article_order,
                "article_sender_type": article_sender_type,
            },
            ticket_id=ticket_id,
        )
        return result
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="get_ticket",
            status="error",
            duration_ms=elapsed,
            params={"ticket_id": ticket_id, "include_articles": include_articles},
            error=str(e),
            ticket_id=ticket_id,
        )
        raise


@mcp.tool(
    description=(
        "Get the articles (customer messages, agent replies, internal notes) "
        "of an OTRS ticket. Use this when the user asks for the ticket "
        "content, conversation summary, or what was said. Returns a list of "
        "articles with Subject, Body, SenderType, IsVisibleForCustomer and "
        "CreateTime."
    )
)
async def get_ticket_articles(
    ticket_id: str,
    limit: int = 20,
    order: str = "desc",
    sender_type: str | None = None,
) -> dict[str, Any]:
    require_scope("read")
    validate_ticket_id(ticket_id)
    if order.lower() not in VALID_ARTICLE_ORDERS:
        raise OTRSValidationError(
            f"order invalido: '{order}'. "
            f"Valores validos: {', '.join(sorted(VALID_ARTICLE_ORDERS))}"
        )
    client = _get_client()
    start = time.monotonic()
    try:
        result = await client.get_ticket_articles(
            ticket_id=ticket_id,
            limit=limit,
            order=order,
            sender_type=sender_type,
        )
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="get_ticket_articles",
            status="success",
            duration_ms=elapsed,
            params={
                "ticket_id": ticket_id,
                "limit": limit,
                "order": order,
                "sender_type": sender_type,
            },
            ticket_id=ticket_id,
        )
        return result
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="get_ticket_articles",
            status="error",
            duration_ms=elapsed,
            params={"ticket_id": ticket_id, "limit": limit},
            error=str(e),
            ticket_id=ticket_id,
        )
        raise


@mcp.tool(description="Search for tickets in OTRS")
async def search_tickets(
    customer_user: str | None = None,
    customer_id: str | None = None,
    queue: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    title: str | None = None,
    limit: int = 50,
    sort_by: str = "Age",
    order_by: str = "Down",
) -> dict[str, Any]:
    require_scope("read")
    client = _get_client()
    start = time.monotonic()
    try:
        result = await client.search_tickets(
            customer_user=customer_user,
            customer_id=customer_id,
            queue=queue,
            state=state,
            priority=priority,
            title=title,
            limit=limit,
            sort_by=sort_by,
            order_by=order_by,
        )
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="search_tickets",
            status="success",
            duration_ms=elapsed,
            params={
                "customer_user": customer_user,
                "queue": queue,
                "state": state,
                "priority": priority,
                "title": title,
                "limit": limit,
            },
        )
        return result
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="search_tickets",
            status="error",
            duration_ms=elapsed,
            params={
                "customer_user": customer_user,
                "queue": queue,
                "state": state,
                "priority": priority,
                "title": title,
                "limit": limit,
            },
            error=str(e),
        )
        raise


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
    require_scope("write")
    validate_ticket_id(ticket_id)
    client = _get_client()

    if priority and priority.lower() not in {p.lower() for p in VALID_PRIORITIES}:
        record_tool_call(
            tool="update_ticket",
            status="error",
            duration_ms=0,
            params={"ticket_id": ticket_id, "priority": priority},
            error=f"Prioridade invalida: {priority}",
            ticket_id=ticket_id,
        )
        raise OTRSValidationError(
            f"Prioridade invalida: '{priority}'. Valores validos: {', '.join(sorted(VALID_PRIORITIES))}"
        )

    start = time.monotonic()
    try:
        result = await client.update_ticket(
            ticket_id=ticket_id,
            title=title,
            queue=queue,
            priority=priority,
            state=state,
            customer_user=customer_user,
            owner=owner,
        )
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="update_ticket",
            status="success",
            duration_ms=elapsed,
            params={
                "ticket_id": ticket_id,
                "title": title,
                "queue": queue,
                "priority": priority,
                "state": state,
            },
            ticket_id=ticket_id,
        )
        return result
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="update_ticket",
            status="error",
            duration_ms=elapsed,
            params={"ticket_id": ticket_id, "title": title, "queue": queue},
            error=str(e),
            ticket_id=ticket_id,
        )
        raise


@mcp.tool(description="Get ticket history from OTRS")
async def get_ticket_history(ticket_id: str) -> dict[str, Any]:
    require_scope("read")
    validate_ticket_id(ticket_id)
    client = _get_client()
    start = time.monotonic()
    try:
        result = await client.get_ticket_history(ticket_id=ticket_id)
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="get_ticket_history",
            status="success",
            duration_ms=elapsed,
            params={"ticket_id": ticket_id},
            ticket_id=ticket_id,
        )
        return result
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="get_ticket_history",
            status="error",
            duration_ms=elapsed,
            params={"ticket_id": ticket_id},
            error=str(e),
            ticket_id=ticket_id,
        )
        raise


@mcp.tool(description="List distinct customer users from recent OTRS tickets")
async def list_customer_users(limit: int = 200) -> dict[str, Any]:
    require_scope("read")
    client = _get_client()
    start = time.monotonic()
    try:
        result = await client.search_customer_users(limit=limit)
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="list_customer_users",
            status="success",
            duration_ms=elapsed,
            params={"limit": limit},
        )
        return result
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        record_tool_call(
            tool="list_customer_users",
            status="error",
            duration_ms=elapsed,
            params={"limit": limit},
            error=str(e),
        )
        raise
