"""Cliente HTTP para a API do OTRS."""

import asyncio
import logging
from typing import Any

import httpx

from otrs_mcp.config import OTRSConfig
from otrs_mcp.exceptions import (
    OTRSAPIError,
    OTRSAuthenticationError,
    OTRSConnectionError,
    OTRSTicketNotFoundError,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 1.0


class OTRSClient:
    """Cliente HTTP para a API do OTRS com sessao, retry e timeout configuravel."""

    def __init__(self, config: OTRSConfig) -> None:
        self._config = config
        self._session_id: str | None = None
        self._http_client: httpx.AsyncClient = httpx.AsyncClient(
            verify=config.verify_ssl,
            follow_redirects=True,
            timeout=config.timeout,
        )
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def close(self) -> None:
        """Fecha o cliente HTTP subjacente."""
        await self._http_client.aclose()

    async def _create_session(self) -> str:
        """Cria uma sessao no OTRS via SessionCreate.

        Segue o mesmo fluxo do script de teste:
        POST {base_url}/SessionCreate com CustomerUserLogin + Password.
        """
        url = f"{self._config.base_url}/SessionCreate"
        payload = {
            "UserLogin": self._config.username,
            "Password": self._config.password,
        }

        response = await self._http_client.post(
            url, json=payload, headers=self._headers
        )
        response.raise_for_status()
        result = response.json()

        if result.get("Error"):
            error_info = result["Error"]
            error_code = (
                error_info.get("ErrorCode", "") if isinstance(error_info, dict) else ""
            )
            error_msg = (
                error_info.get("ErrorMessage", "")
                if isinstance(error_info, dict)
                else str(error_info)
            )

            if "AuthFail" in error_code:
                raise OTRSAuthenticationError(
                    f"Falha na autenticacao: {error_msg}",
                    details={"error_code": error_code},
                )
            raise OTRSAPIError(
                f"Erro ao criar sessao: {error_msg}",
                response_body=str(result),
            )

        session_id = result.get("SessionID")
        if not session_id or not str(session_id).strip():
            raise OTRSAuthenticationError(
                "SessionCreate retornou HTTP 200 mas sem SessionID valida",
                details={"response": result},
            )

        session_id = str(session_id).strip()
        logger.info("Sessao OTRS criada com sucesso")
        return session_id

    async def _ensure_session(self) -> str:
        """Garante que existe uma sessao ativa, criando uma se necessario."""
        if self._session_id is None:
            self._session_id = await self._create_session()
        return self._session_id

    def _invalidate_session(self) -> None:
        """Invalida a sessao atual para forcar recriacao."""
        self._session_id = None

    async def request(
        self, operation: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Envia requisicao autenticada para a API do OTRS com retry.

        Usa apenas SessionID para autenticação após o login inicial.
        Credenciais só são enviadas novamente se a sessão expirar.
        """
        url = f"{self._config.base_url}/{operation}"
        session_id = await self._ensure_session()

        # Usa apenas SessionID para requests normais (mais seguro)
        request_data: dict[str, Any] = {
            "SessionID": session_id,
        }
        if data:
            request_data.update(data)

        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._http_client.post(
                    url, json=request_data, headers=self._headers
                )
                response.raise_for_status()
                result = response.json()

                if result.get("Error"):
                    error_info = result["Error"]
                    error_code = (
                        error_info.get("ErrorCode", "")
                        if isinstance(error_info, dict)
                        else ""
                    )
                    error_msg = (
                        error_info.get("ErrorMessage", "")
                        if isinstance(error_info, dict)
                        else str(error_info)
                    )

                    if "AuthFail" in error_code:
                        if attempt < MAX_RETRIES:
                            logger.warning(
                                "Sessao expirada em %s, recriando (tentativa %d/%d)",
                                operation,
                                attempt,
                                MAX_RETRIES,
                            )
                            self._invalidate_session()
                            session_id = await self._ensure_session()
                            request_data["SessionID"] = session_id
                            await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))
                            continue
                        raise OTRSAuthenticationError(
                            f"Sessao expirada apos {MAX_RETRIES} tentativas",
                            details={"error_code": error_code},
                        )

                    if (
                        "not found" in error_msg.lower()
                        or "no ticket" in error_msg.lower()
                    ):
                        raise OTRSTicketNotFoundError(
                            f"Ticket nao encontrado: {error_msg}",
                            details={"operation": operation, "response": result},
                        )

                    raise OTRSAPIError(
                        f"Erro de aplicacao: {error_msg}",
                        response_body=str(result),
                    )

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
                if e.response.status_code == 401 and attempt < MAX_RETRIES:
                    self._invalidate_session()
                    session_id = await self._ensure_session()
                    request_data["SessionID"] = session_id
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
            status_code = last_error.response.status_code
            if status_code == 401:
                raise OTRSAuthenticationError(
                    "Credenciais OTRS invalidas",
                    details={"status_code": status_code},
                )
            raise OTRSAPIError(
                f"Erro HTTP {status_code}",
                status_code=status_code,
                response_body=last_error.response.text,
            )

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
        ticket_obj = {
            "Title": title,
            "Queue": queue or self._config.default_queue,
            "Priority": priority or self._config.default_priority,
            "State": state or self._config.default_state,
            "CustomerUser": customer_user or self._config.username,
        }
        
        type_val = ticket_type or self._config.default_type
        if type_val:
            ticket_obj["Type"] = type_val

        ticket_data = {
            "Ticket": ticket_obj,
            "Article": {
                "Subject": title,
                "Body": body,
                "ContentType": "text/plain; charset=utf8",
                "ArticleType": "note-external",
                "TimeUnit": 1,
            },
        }
        result = await self.request("TicketCreate", ticket_data)
        if not result.get("Error") and result.get("TicketID"):
            result["WebURL"] = self._config.get_ticket_web_url(str(result["TicketID"]))
        return result

    async def search_tickets(
        self,
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
        search_data: dict[str, Any] = {
            "Limit": limit,
            "Result": "ARRAY",
            "SortBy": sort_by,
            "OrderBy": order_by,
        }
        if customer_user:
            search_data["CustomerUserLogin"] = customer_user
        if customer_id:
            search_data["CustomerID"] = customer_id
        if queue:
            search_data["Queues"] = [queue]
        if state:
            search_data["States"] = [state]
        if priority:
            search_data["Priorities"] = [priority]
        if title:
            search_data["Title"] = title.replace("*", "%")

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
