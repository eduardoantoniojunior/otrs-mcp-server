"""Testes para o cliente HTTP do OTRS."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from otrs_mcp.client import OTRSClient, MAX_RETRIES
from otrs_mcp.config import OTRSConfig
from otrs_mcp.exceptions import OTRSConnectionError


@pytest.fixture
def config() -> OTRSConfig:
    """Configuracao para testes."""
    return OTRSConfig(
        base_url="https://test.example.com/otrs/nph-genericinterface.pl/Webservice/Test",
        username="user",
        password="pass",
        verify_ssl=False,
        timeout=10,
    )


@pytest.fixture
def client(config: OTRSConfig) -> OTRSClient:
    """Cliente para testes."""
    return OTRSClient(config)


def _mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Cria uma resposta HTTP mockada."""
    response = httpx.Response(status_code=status_code, json=json_data)
    response.raise_for_status = lambda: None
    return response


class TestOTRSClientRequest:
    """Testes para o metodo request do OTRSClient."""

    @pytest.mark.asyncio
    async def test_request_success(self, client: OTRSClient) -> None:
        """Requisicao bem-sucedida deve retornar dados."""
        mock_response = _mock_response({"TicketID": "123"})

        with patch("otrs_mcp.client.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            result = await client.request("TicketGet", {"TicketID": "123"})

            assert result == {"TicketID": "123"}
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_includes_auth(self, client: OTRSClient) -> None:
        """Requisicao deve incluir credenciais de autenticacao."""
        mock_response = _mock_response({})

        with patch("otrs_mcp.client.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            await client.request("TicketGet")

            call_args = mock_client.post.call_args
            json_data = call_args.kwargs.get("json") or call_args[1].get("json")
            assert json_data["UserLogin"] == "user"
            assert json_data["Password"] == "pass"

    @pytest.mark.asyncio
    async def test_request_retry_on_http_error(self, client: OTRSClient) -> None:
        """Requisicao deve retry em caso de erro HTTP."""
        error_response = httpx.Response(status_code=500, text="Server Error")
        error_response.raise_for_status = lambda: (_ for _ in ()).throw(
            httpx.HTTPStatusError("Server Error", request=httpx.Request("POST", "http://test"), response=error_response)
        )

        success_response = _mock_response({"TicketID": "123"})

        with patch("otrs_mcp.client.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.side_effect = [error_response, success_response]
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
                result = await client.request("TicketGet")

            assert result == {"TicketID": "123"}
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_request_raises_connection_error_after_retries(self, client: OTRSClient) -> None:
        """Requisicao deve levantar OTRSConnectionError apos falhas de conexao."""
        with patch("otrs_mcp.client.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(OTRSConnectionError, match="Falha apos"):
                    await client.request("TicketGet")


class TestOTRSClientGetTicket:
    """Testes para o metodo get_ticket."""

    @pytest.mark.asyncio
    async def test_get_ticket_success(self, client: OTRSClient) -> None:
        """get_ticket deve retornar dados do ticket."""
        mock_response = _mock_response({"TicketID": "123", "Title": "Test"})

        with patch("otrs_mcp.client.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            result = await client.get_ticket("123")

            assert result["TicketID"] == "123"
            assert "WebURL" in result
            assert "HistoryWebURL" in result


class TestOTRSClientCreateTicket:
    """Testes para o metodo create_ticket."""

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, client: OTRSClient) -> None:
        """create_ticket deve criar ticket e retornar dados."""
        mock_response = _mock_response({"TicketID": "456"})

        with patch("otrs_mcp.client.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            result = await client.create_ticket("Test Title", "Test Body")

            assert result["TicketID"] == "456"
            assert "WebURL" in result


class TestOTRSClientSearchTickets:
    """Testes para o metodo search_tickets."""

    @pytest.mark.asyncio
    async def test_search_tickets_success(self, client: OTRSClient) -> None:
        """search_tickets deve retornar lista de tickets."""
        mock_response = _mock_response({"TicketID": ["123", "456"]})

        with patch("otrs_mcp.client.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            result = await client.search_tickets(limit=10)

            assert result["TicketID"] == ["123", "456"]
            assert "WebSearchURL" in result
            assert "TicketWebURLs" in result


class TestOTRSClientUpdateTicket:
    """Testes para o metodo update_ticket."""

    @pytest.mark.asyncio
    async def test_update_ticket_success(self, client: OTRSClient) -> None:
        """update_ticket deve atualizar ticket."""
        mock_response = _mock_response({"TicketID": "123"})

        with patch("otrs_mcp.client.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            result = await client.update_ticket("123", title="New Title")

            assert result["TicketID"] == "123"
            assert "WebURL" in result


class TestOTRSClientGetTicketHistory:
    """Testes para o metodo get_ticket_history."""

    @pytest.mark.asyncio
    async def test_get_ticket_history_success(self, client: OTRSClient) -> None:
        """get_ticket_history deve retornar historico do ticket."""
        mock_response = _mock_response({"TicketID": "123", "History": []})

        with patch("otrs_mcp.client.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.return_value = mock_client

            result = await client.get_ticket_history("123")

            assert result["TicketID"] == "123"
            assert "WebURL" in result
            assert "HistoryWebURL" in result
