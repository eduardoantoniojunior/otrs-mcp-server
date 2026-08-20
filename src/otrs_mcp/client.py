"""Cliente HTTP para a API do OTRS."""

import asyncio
import logging
from typing import Any

import httpx

from otrs_mcp.config import OTRSConfig
from otrs_mcp.exceptions import OTRSAPIError, OTRSConnectionError

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 1.0


class OTRSClient:
    """Cliente HTTP para a API do OTRS com retry e timeout configuravel."""

    def __init__(self, config: OTRSConfig) -> None:
        self._config = config
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def request(
        self, operation: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Envia requisicao autenticada para a API do OTRS com retry."""
        url = f"{self._config.base_url}/{operation}"

        request_data: dict[str, Any] = {
            "UserLogin": self._config.username,
            "Password": self._config.password,
        }
        if data:
            request_data.update(data)

        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    verify=self._config.verify_ssl,
                    follow_redirects=True,
                    timeout=self._config.timeout,
                ) as client:
                    response = await client.post(
                        url, json=request_data, headers=self._headers
                    )
                    response.raise_for_status()
                    result = response.json()

                    if self._config.debug:
                        logger.debug(
                            "Requisicao %s OK (tentativa %d/%d)",
                            operation,
                            attempt,
                            MAX_RETRIES,
                        )

                    return result

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    "Erro HTTP %d em %s (tentativa %d/%d): %s",
                    e.response.status_code,
                    operation,
                    attempt,
                    MAX_RETRIES,
                    e,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))

            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    "Erro de conexao em %s (tentativa %d/%d): %s",
                    operation,
                    attempt,
                    MAX_RETRIES,
                    e,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))

        if isinstance(last_error, httpx.HTTPStatusError):
            return {"Error": f"HTTP {last_error.response.status_code}: {last_error.response.text}"}

        raise OTRSConnectionError(f"Falha apos {MAX_RETRIES} tentativas: {last_error}")

    async def get_ticket(
        self,
        ticket_id: str,
        include_dynamic_fields: bool = True,
        include_extended_data: bool = True,
    ) -> dict[str, Any]:
        data = {
            "TicketID": ticket_id,
            "DynamicFields": 1 if include_dynamic_fields else 0,
            "Extended": 1 if include_extended_data else 0,
        }
        result = await self.request("TicketGet", data)
        result["WebURL"] = self._config.get_ticket_web_url(ticket_id)
        result["HistoryWebURL"] = self._config.get_ticket_history_web_url(ticket_id)
        return result

    async def create_ticket(
        self,
        title: str,
        body: str,
        queue: str | None = None,
        priority: str | None = None,
        state: str | None = None,
        customer_user: str | None = None,
        ticket_type: str | None = None,
    ) -> dict[str, Any]:
        ticket_data = {
            "Ticket": {
                "Title": title,
                "Queue": queue or self._config.default_queue,
                "Priority": priority or self._config.default_priority,
                "State": state or self._config.default_state,
                "Type": ticket_type or self._config.default_type,
                "CustomerUser": customer_user or "Internal",
            },
            "Article": {
                "Subject": title,
                "Body": body,
                "ContentType": "text/plain; charset=utf8",
                "ArticleType": "note-external",
            },
        }
        result = await self.request("TicketCreate", ticket_data)
        if not result.get("Error") and result.get("TicketID"):
            result["WebURL"] = self._config.get_ticket_web_url(str(result["TicketID"]))
        return result

    async def search_tickets(
        self,
        customer_user: str | None = None,
        queue: str | None = None,
        state: str | None = None,
        priority: str | None = None,
        title: str | None = None,
        limit: int = 50,
        sort_by: str = "Age",
        order_by: str = "Down",
    ) -> dict[str, Any]:
        search_data: dict[str, Any] = {
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

        result = await self.request("TicketSearch", search_data)

        if result.get("TicketID") and isinstance(result["TicketID"], list):
            result["WebSearchURL"] = self._config.get_ticket_search_web_url()
            result["TicketWebURLs"] = [
                {
                    "TicketID": tid,
                    "WebURL": self._config.get_ticket_web_url(str(tid)),
                }
                for tid in result["TicketID"]
            ]

        return result

    async def update_ticket(
        self,
        ticket_id: str,
        title: str | None = None,
        queue: str | None = None,
        priority: str | None = None,
        state: str | None = None,
        customer_user: str | None = None,
        owner: str | None = None,
    ) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if title:
            updates["Title"] = title
        if queue:
            updates["Queue"] = queue
        if priority:
            updates["Priority"] = priority
        if state:
            updates["State"] = state
        if customer_user:
            updates["CustomerUser"] = customer_user
        if owner:
            updates["Owner"] = owner

        update_data = {"TicketID": ticket_id, "Ticket": updates}
        result = await self.request("TicketUpdate", update_data)
        result["WebURL"] = self._config.get_ticket_web_url(ticket_id)
        return result

    async def get_ticket_history(self, ticket_id: str) -> dict[str, Any]:
        history_data = {"TicketID": ticket_id}
        result = await self.request("TicketHistoryGet", history_data)
        result["WebURL"] = self._config.get_ticket_web_url(ticket_id)
        result["HistoryWebURL"] = self._config.get_ticket_history_web_url(ticket_id)
        return result
