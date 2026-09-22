"""Cliente HTTP para a API do OTRS."""

import asyncio
import logging
from typing import Any

import httpx

from otrs_mcp.config import OTRSConfig
from otrs_mcp.constants import ARTICLE_WHITELIST_FIELDS
from otrs_mcp.exceptions import (
    OTRSAPIError,
    OTRSAuthenticationError,
    OTRSConnectionError,
    OTRSTicketNotFoundError,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 1.0


def _extract_ticket_data(result: dict[str, Any]) -> dict[str, Any] | None:
    """Extrai o dict do ticket de uma resposta de TicketGet.

    O Ticket Connector do OTRS as vezes devolve `Ticket` como lista de um
    unico dict, as vezes como dict direto, dependendo da versao.
    """
    ticket = result.get("Ticket")
    if isinstance(ticket, list):
        return ticket[0] if ticket else None
    if isinstance(ticket, dict):
        return ticket
    return None


def _extract_raw_articles(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrai a lista bruta de artigos de uma resposta de TicketGet.

    Locais possiveis segundo a versao/configuracao do OTRS:
    - `result["Article"]` (top-level, formato antigo)
    - `result["Articles"]` (top-level, formato novo)
    - `result["Ticket"]["Article"]` (dentro do ticket)
    - `result["Ticket"]["Articles"]` (dentro do ticket)
    """
    for key in ("Article", "Articles"):
        raw = result.get(key)
        if raw is not None:
            return [raw] if isinstance(raw, dict) else list(raw)

    ticket_data = _extract_ticket_data(result)
    if ticket_data:
        for key in ("Article", "Articles"):
            raw = ticket_data.get(key)
            if raw is not None:
                return [raw] if isinstance(raw, dict) else list(raw)

    return []


def _sanitize_article(article: dict[str, Any]) -> dict[str, Any]:
    """Aplica o whitelist de campos a um artigo bruto do OTRS."""
    return {k: v for k, v in article.items() if k in ARTICLE_WHITELIST_FIELDS}


def _sort_articles(articles: list[dict[str, Any]], order: str) -> list[dict[str, Any]]:
    """Ordena artigos por CreateTime (ISO string ordena lexicograficamente),
    com ArticleID como criterio de desempate."""

    def sort_key(article: dict[str, Any]) -> tuple[str, int]:
        create_time = str(article.get("CreateTime", ""))
        try:
            article_id = int(article.get("ArticleID", 0) or 0)
        except (TypeError, ValueError):
            article_id = 0
        return (create_time, article_id)

    reverse = order.lower() == "desc"
    return sorted(articles, key=sort_key, reverse=reverse)


class OTRSClient:
    """Cliente HTTP para a API do OTRS com sessao, retry e timeout configuravel."""

    def __init__(self, config: OTRSConfig) -> None:
        self._config = config
        self._session_id: str | None = None
        self._session_lock = asyncio.Lock()
        self._discovered_type: str | None = None
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
        if self._session_id is not None:
            return self._session_id
        async with self._session_lock:
            # Double-check após adquirir o lock
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
        include_articles: bool = False,
        article_limit: int | None = None,
        article_order: str = "desc",
        article_sender_type: str | None = None,
    ) -> dict[str, Any]:
        """Retorna dados de um ticket com links para a interface web.

        Args:
            ticket_id: ID do ticket.
            include_dynamic_fields: Inclui dynamic fields no retorno.
            include_extended_data: Inclui dados estendidos do ticket.
            include_articles: Se True, adiciona `Articles` (lista) com o
                corpo dos artigos ja sanitizados por whitelist. Aumenta o
                payload significativamente; default False.
            article_limit: Quando `include_articles=True`, limita a
                quantidade de artigos retornados (apos aplicar order).
            article_order: `"desc"` (default, mais novos primeiro) ou
                `"asc"`. Ordenacao por `CreateTime` com `ArticleID` como
                desempate.
            article_sender_type: Filtra artigos por `SenderType` (ex.
                "customer", "agent", "system"). Aplicado antes do limit.
        """
        data: dict[str, Any] = {
            "TicketID": ticket_id,
            "DynamicFields": 1 if include_dynamic_fields else 0,
            "Extended": 1 if include_extended_data else 0,
        }
        if include_articles:
            # AllArticles=1 e' a chave usada pelo Ticket Connector para
            # retornar os corpos dos artigos junto do ticket.
            data["AllArticles"] = 1

        result = await self.request("TicketGet", data)

        if include_articles:
            raw_articles = _extract_raw_articles(result)
            if article_sender_type:
                raw_articles = [
                    a
                    for a in raw_articles
                    if str(a.get("SenderType", "")).lower()
                    == article_sender_type.lower()
                ]
            ordered = _sort_articles(raw_articles, article_order)
            if article_limit is not None and article_limit >= 0:
                ordered = ordered[:article_limit]
            sanitized = [_sanitize_article(a) for a in ordered]

            # Remove Article/Articles brutos do payload devolvido ao cliente:
            # o retorno canonico passa a ser `Articles` sanitizado.
            result.pop("Article", None)
            result.pop("Articles", None)
            ticket_data = _extract_ticket_data(result)
            if isinstance(ticket_data, dict):
                ticket_data.pop("Article", None)
                ticket_data.pop("Articles", None)

            result["Articles"] = sanitized
            result["ArticleCount"] = len(sanitized)

        result["WebURL"] = self._config.get_ticket_web_url(ticket_id)
        result["HistoryWebURL"] = self._config.get_ticket_history_web_url(ticket_id)
        return result

    async def get_ticket_articles(
        self,
        ticket_id: str,
        limit: int = 20,
        order: str = "desc",
        sender_type: str | None = None,
    ) -> dict[str, Any]:
        """Retorna apenas os artigos (corpo) de um ticket.

        Wrapper focado em conteudo: dispara `get_ticket` com
        `include_articles=True` e devolve so o essencial para o consumidor
        de MCP que quer ler o conversa do ticket sem receber metadados
        completos.
        """
        result = await self.get_ticket(
            ticket_id=ticket_id,
            include_dynamic_fields=False,
            include_extended_data=False,
            include_articles=True,
            article_limit=limit,
            article_order=order,
            article_sender_type=sender_type,
        )
        return {
            "TicketID": ticket_id,
            "Articles": result.get("Articles", []),
            "ArticleCount": result.get("ArticleCount", 0),
            "WebURL": result.get("WebURL"),
            "HistoryWebURL": result.get("HistoryWebURL"),
        }

    async def _discover_default_type(self) -> str:
        """Descobre o Type valido buscando um ticket existente no OTRS.

        Faz TicketSearch(limit=1) + TicketGet para extrair o campo Type
        de um ticket real. O resultado e cacheado em _discovered_type
        para evitar chamadas repetidas.

        Returns:
            Nome do Type encontrado, ou string vazia se nao conseguir.
        """
        if self._discovered_type is not None:
            return self._discovered_type

        try:
            search = await self.request(
                "TicketSearch",
                {
                    "Limit": 1,
                    "Result": "ARRAY",
                    "SortBy": "Age",
                    "OrderBy": "Down",
                },
            )
            ticket_ids = search.get("TicketID", [])
            if not ticket_ids:
                logger.warning("Nenhum ticket encontrado para descobrir o Type padrao")
                self._discovered_type = ""
                return ""

            tid = ticket_ids[0] if isinstance(ticket_ids, list) else ticket_ids
            ticket = await self.request("TicketGet", {"TicketID": str(tid)})

            ticket_data = ticket.get("Ticket")
            if isinstance(ticket_data, list):
                ticket_data = ticket_data[0] if ticket_data else {}

            discovered = (
                ticket_data.get("Type", "") if isinstance(ticket_data, dict) else ""
            )
            self._discovered_type = discovered
            if discovered:
                logger.info("Type padrao descoberto do OTRS: '%s'", discovered)
            else:
                logger.warning("Ticket %s nao tem campo Type", tid)
            return discovered
        except Exception as e:
            logger.warning("Falha ao descobrir Type padrao: %s", e)
            self._discovered_type = ""
            return ""

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
        if not type_val:
            type_val = await self._discover_default_type()
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

    async def search_customer_users(
        self,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Lista customer users distintos a partir dos tickets existentes.

        Como a operacao CustomerUserSearch nao esta disponivel no webservice,
        usa TicketSearch + TicketGet para extrair os customer users unicos
        dos tickets mais recentes.

        Args:
            limit: Maximo de tickets a consultar (default: 200).

        Returns:
            Dicionario com CustomerUsers: lista de {Login, Name, CustomerID}.
        """
        search_result = await self.search_tickets(
            limit=limit,
            sort_by="Age",
            order_by="Down",
        )

        ticket_ids = search_result.get("TicketID", [])
        if not ticket_ids:
            return {"CustomerUsers": []}
        if not isinstance(ticket_ids, list):
            ticket_ids = [ticket_ids]

        seen: set[str] = set()
        customers: list[dict[str, str]] = []

        for tid in ticket_ids:
            try:
                ticket = await self.get_ticket(
                    str(tid),
                    include_dynamic_fields=False,
                    include_extended_data=False,
                )
                # TicketGet retorna Ticket como lista ou dict
                ticket_data = ticket.get("Ticket")
                if isinstance(ticket_data, list):
                    ticket_data = ticket_data[0] if ticket_data else {}
                if not isinstance(ticket_data, dict):
                    continue

                login = ticket_data.get("CustomerUserID", "")
                if not login or login in seen:
                    continue
                seen.add(login)
                customers.append(
                    {
                        "Login": login,
                        "Name": ticket_data.get("CustomerName", login),
                        "CustomerID": ticket_data.get("CustomerID", ""),
                    }
                )
            except Exception:
                continue

        return {"CustomerUsers": customers}
