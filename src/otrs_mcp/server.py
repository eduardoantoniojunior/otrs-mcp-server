#!/usr/bin/env python

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import dotenv
import httpx
from mcp.server.fastmcp import FastMCP

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("OTRS API MCP")


@dataclass
class OTRSConfig:
    base_url: str = os.environ.get("OTRS_BASE_URL", "")
    username: str = os.environ.get("OTRS_USERNAME", "")
    password: str = os.environ.get("OTRS_PASSWORD", "")
    verify_ssl: bool = os.getenv("OTRS_VERIFY_SSL", "false").lower() == "true"
    timeout: int = int(os.getenv("OTRS_TIMEOUT", "30"))
    default_queue: str = os.getenv("OTRS_DEFAULT_QUEUE", "Raw")
    default_state: str = os.getenv("OTRS_DEFAULT_STATE", "new")
    default_priority: str = os.getenv("OTRS_DEFAULT_PRIORITY", "3 normal")
    default_type: str = os.getenv("OTRS_DEFAULT_TYPE", "Unclassified")
    web_base_url: str = os.getenv("OTRS_WEB_BASE_URL", "")

    def __post_init__(self) -> None:
        missing = []
        if not self.base_url:
            missing.append("OTRS_BASE_URL")
        if not self.username:
            missing.append("OTRS_USERNAME")
        if not self.password:
            missing.append("OTRS_PASSWORD")
        if missing:
            raise ValueError(
                f"Variaveis de ambiente obrigatorias nao configuradas: {', '.join(missing)}"
            )
        if not self.web_base_url:
            self.web_base_url = self.base_url.rsplit("/nph-genericinterface.pl", 1)[0]


config = OTRSConfig()


def get_ticket_web_url(ticket_id: str) -> str:
    return f"{config.web_base_url}/index.pl?Action=AgentTicketZoom;TicketID={ticket_id}"


def get_ticket_history_web_url(ticket_id: str) -> str:
    return f"{config.web_base_url}/index.pl?Action=AgentTicketHistory;TicketID={ticket_id}"


def get_ticket_search_web_url() -> str:
    return f"{config.web_base_url}/index.pl?Action=AgentTicketSearch"


async def make_api_request_with_auth(
    operation: str, data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    url = f"{config.base_url}/{operation}"

    request_data: Dict[str, Any] = {
        "UserLogin": config.username,
        "Password": config.password,
    }
    if data:
        request_data.update(data)

    try:
        async with httpx.AsyncClient(
            verify=config.verify_ssl,
            follow_redirects=True,
            timeout=config.timeout,
        ) as client:
            response = await client.post(
                url,
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Erro HTTP %d em %s: %s", e.response.status_code, operation, e)
        return {"Error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except httpx.RequestError as e:
        logger.error("Erro de conexao em %s: %s", operation, e)
        return {"Error": f"Erro de conexao: {e}"}


VALID_QUEUES = frozenset({"Raw", "Junk", "Misc"})
VALID_PRIORITIES = frozenset({"1 low", "2 normal", "3 normal", "4 high"})


@mcp.tool(description="Create a new ticket in OTRS")
async def create_ticket(
    title: str,
    body: str,
    queue: Optional[str] = None,
    priority: Optional[str] = None,
    state: Optional[str] = None,
    customer_user: Optional[str] = None,
    ticket_type: Optional[str] = None,
) -> Dict[str, Any]:
    resolved_customer_user = "Internal"
    resolved_queue = queue if queue in VALID_QUEUES else config.default_queue

    priority_variations = ["3 normal", "1 Low", "2 normal", "4 high"]
    if priority:
        priority_variations = [priority] + priority_variations

    attempts: List[Dict[str, Any]] = []

    for priority_attempt in priority_variations:
        ticket_data = {
            "Ticket": {
                "Title": title,
                "Queue": resolved_queue,
                "Priority": priority_attempt,
                "State": state or config.default_state,
                "Type": ticket_type or config.default_type,
                "CustomerUser": resolved_customer_user,
            },
            "Article": {
                "Subject": title,
                "Body": body,
                "ContentType": "text/plain; charset=utf8",
                "ArticleType": "note-external",
            },
        }

        result = await make_api_request_with_auth("TicketCreate", ticket_data)

        attempt_info = {
            "priority_tried": priority_attempt,
            "success": not result.get("Error"),
            "error": result.get("Error"),
            "ticket_id": result.get("TicketID"),
        }
        attempts.append(attempt_info)

        if not result.get("Error"):
            if result.get("TicketID"):
                result["WebURL"] = get_ticket_web_url(str(result["TicketID"]))
            result["_attempts"] = len(attempts)
            return result
        elif "Priority" not in str(result.get("Error", {})) and "CustomerUser" not in str(
            result.get("Error", {})
        ):
            result["_attempts"] = len(attempts)
            return result

    result["_attempts"] = len(attempts)
    result["_priorities_tried"] = [a["priority_tried"] for a in attempts]
    return result


@mcp.tool(description="Get ticket details from OTRS")
async def get_ticket(
    ticket_id: str,
    include_dynamic_fields: bool = True,
    include_extended_data: bool = True,
) -> Dict[str, Any]:
    ticket_data = {
        "TicketID": ticket_id,
        "DynamicFields": 1 if include_dynamic_fields else 0,
        "Extended": 1 if include_extended_data else 0,
    }

    result = await make_api_request_with_auth("TicketGet", ticket_data)

    result["WebURL"] = get_ticket_web_url(ticket_id)
    result["HistoryWebURL"] = get_ticket_history_web_url(ticket_id)

    return result


@mcp.tool(description="Search for tickets in OTRS")
async def search_tickets(
    customer_user: Optional[str] = None,
    queue: Optional[str] = None,
    state: Optional[str] = None,
    priority: Optional[str] = None,
    title: Optional[str] = None,
    limit: int = 50,
    sort_by: str = "Age",
    order_by: str = "Down",
) -> Dict[str, Any]:
    search_data: Dict[str, Any] = {
        "Limit": limit,
        "Result": "ARRAY",
        "SortBy": sort_by,
        "OrderBy": order_by,
    }

    if customer_user:
        search_data["CustomerUserLogin"] = customer_user
    if queue:
        search_data["Queues"] = [queue]
    if state:
        search_data["States"] = [state]
    if priority:
        search_data["Priorities"] = [priority]
    if title:
        search_data["Title"] = title

    result = await make_api_request_with_auth("TicketSearch", search_data)

    if result.get("TicketID") and isinstance(result["TicketID"], list):
        result["WebSearchURL"] = get_ticket_search_web_url()
        result["TicketWebURLs"] = [
            {
                "TicketID": ticket_id,
                "WebURL": get_ticket_web_url(str(ticket_id)),
            }
            for ticket_id in result["TicketID"]
        ]

    return result


@mcp.tool(description="Update an existing ticket in OTRS")
async def update_ticket(
    ticket_id: str,
    title: Optional[str] = None,
    queue: Optional[str] = None,
    priority: Optional[str] = None,
    state: Optional[str] = None,
    customer_user: Optional[str] = None,
    owner: Optional[str] = None,
) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}
    if title:
        updates["Title"] = title
    if queue:
        updates["Queue"] = queue
    if state:
        updates["State"] = state
    if customer_user:
        updates["CustomerUser"] = customer_user
    if owner:
        updates["Owner"] = owner

    if priority:
        priority_variations = [priority, "3 normal", "1 Low", "2 normal", "4 high"]

        for priority_attempt in priority_variations:
            test_updates = updates.copy()
            test_updates["Priority"] = priority_attempt

            update_data = {"TicketID": ticket_id, "Ticket": test_updates}
            result = await make_api_request_with_auth("TicketUpdate", update_data)

            if not result.get("Error"):
                result["WebURL"] = get_ticket_web_url(ticket_id)
                return result
            elif "Priority" not in str(result.get("Error", {})):
                result["WebURL"] = get_ticket_web_url(ticket_id)
                return result

        result["WebURL"] = get_ticket_web_url(ticket_id)
        return result
    else:
        update_data = {"TicketID": ticket_id, "Ticket": updates}
        result = await make_api_request_with_auth("TicketUpdate", update_data)
        result["WebURL"] = get_ticket_web_url(ticket_id)
        return result


@mcp.tool(description="Get ticket history from OTRS")
async def get_ticket_history(ticket_id: str) -> Dict[str, Any]:
    history_data = {"TicketID": ticket_id}

    result = await make_api_request_with_auth("TicketHistoryGet", history_data)

    result["WebURL"] = get_ticket_web_url(ticket_id)
    result["HistoryWebURL"] = get_ticket_history_web_url(ticket_id)

    return result


@mcp.resource("otrs://ticket/{ticket_id}")
async def ticket_resource(ticket_id: str) -> str:
    try:
        ticket = await get_ticket(ticket_id=ticket_id)
        return json.dumps(ticket, indent=2)
    except Exception as e:
        logger.error("Erro ao obter ticket %s: %s", ticket_id, e)
        return f"Error retrieving ticket: {e}"


@mcp.resource("otrs://ticket/{ticket_id}/history")
async def ticket_history_resource(ticket_id: str) -> str:
    try:
        history = await get_ticket_history(ticket_id=ticket_id)
        return json.dumps(history, indent=2)
    except Exception as e:
        logger.error("Erro ao obter historico do ticket %s: %s", ticket_id, e)
        return f"Error retrieving ticket history: {e}"


@mcp.resource("otrs://search/tickets")
async def search_tickets_resource() -> str:
    try:
        tickets = await search_tickets(limit=20)
        return json.dumps(tickets, indent=2)
    except Exception as e:
        logger.error("Erro ao buscar tickets: %s", e)
        return f"Error searching tickets: {e}"


if __name__ == "__main__":
    logger.info("Starting OTRS MCP Server...")
    mcp.run()
