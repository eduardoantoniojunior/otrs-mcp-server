"""Testes para o cliente HTTP do OTRS."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from otrs_mcp.client import MAX_RETRIES, OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.exceptions import (
    OTRSAPIError,
    OTRSAuthenticationError,
    OTRSConnectionError,
)


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
    request = httpx.Request("POST", "http://test.example.com")
    response = httpx.Response(status_code=status_code, json=json_data, request=request)
    return response


def _session_response() -> httpx.Response:
    """Cria uma resposta mockada de SessionCreate."""
    return _mock_response({"SessionID": "test-session-id-123"})


def _setup_client_mock(client: OTRSClient, *responses: httpx.Response) -> AsyncMock:
    """Configura mock do _http_client no OTRSClient."""
    mock_http = AsyncMock()
    mock_http.post.side_effect = list(responses)
    client._http_client = mock_http
    return mock_http


class TestOTRSClientRequest:
    """Testes para o metodo request do OTRSClient."""

    @pytest.mark.asyncio
    async def test_request_success(self, client: OTRSClient) -> None:
        """Requisicao bem-sucedida deve retornar dados."""
        mock_http = _setup_client_mock(
            client, _session_response(), _mock_response({"TicketID": "123"})
        )

        result = await client.request("TicketGet", {"TicketID": "123"})

        assert result == {"TicketID": "123"}
        assert mock_http.post.call_count == 2

    @pytest.mark.asyncio
    async def test_request_includes_auth(self, client: OTRSClient) -> None:
        """Requisicao deve incluir SessionID (credenciais apenas na criacao de sessao)."""
        mock_http = _setup_client_mock(client, _session_response(), _mock_response({}))

        await client.request("TicketGet")

        # Sessao: deve enviar credenciais
        session_call = mock_http.post.call_args_list[0]
        session_json = session_call.kwargs.get("json") or session_call[1].get("json")
        assert session_json["UserLogin"] == "user"
        assert session_json["Password"] == "pass"
        assert "SessionID" not in session_json

        # Request: usa apenas SessionID (mais seguro)
        request_call = mock_http.post.call_args_list[1]
        request_json = request_call.kwargs.get("json") or request_call[1].get("json")
        assert request_json["SessionID"] == "test-session-id-123"
        # Credenciais NAO devem ser enviadas em requests normais
        assert "UserLogin" not in request_json
        assert "Password" not in request_json

    @pytest.mark.asyncio
    async def test_request_reuses_session(self, client: OTRSClient) -> None:
        """Sessao criada uma vez deve ser reutilizada."""
        mock_http = _setup_client_mock(
            client,
            _session_response(),
            _mock_response({"TicketID": "1"}),
            _mock_response({"TicketID": "2"}),
        )

        await client.request("TicketGet", {"TicketID": "1"})
        await client.request("TicketGet", {"TicketID": "2"})

        assert mock_http.post.call_count == 3

        first_call_json = mock_http.post.call_args_list[0].kwargs.get("json")
        assert "SessionID" not in first_call_json

        second_call_json = mock_http.post.call_args_list[1].kwargs.get("json")
        assert second_call_json["SessionID"] == "test-session-id-123"

        third_call_json = mock_http.post.call_args_list[2].kwargs.get("json")
        assert third_call_json["SessionID"] == "test-session-id-123"

    @pytest.mark.asyncio
    async def test_request_retry_on_http_error(self, client: OTRSClient) -> None:
        """Requisicao deve retry em caso de erro HTTP."""
        error_response = httpx.Response(
            status_code=500,
            text="Server Error",
            request=httpx.Request("POST", "http://test"),
        )

        mock_http = _setup_client_mock(
            client,
            _session_response(),
            error_response,
            _mock_response({"TicketID": "123"}),
        )

        with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.request("TicketGet")

        assert result == {"TicketID": "123"}
        assert mock_http.post.call_count == 3

    @pytest.mark.asyncio
    async def test_request_raises_connection_error_after_retries(
        self, client: OTRSClient
    ) -> None:
        """Requisicao deve levantar OTRSConnectionError apos falhas de conexao."""
        # Session creation succeeds, then all request attempts fail
        mock_http = _setup_client_mock(client)
        mock_http.post.side_effect = [
            _session_response(),  # _create_session
            httpx.ConnectError("Connection refused"),  # attempt 1
            httpx.ConnectError("Connection refused"),  # attempt 2
            httpx.ConnectError("Connection refused"),  # attempt 3
        ]

        with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OTRSConnectionError, match="Falha apos"):
                await client.request("TicketGet")

    @pytest.mark.asyncio
    async def test_request_raises_auth_error_on_401(self, client: OTRSClient) -> None:
        """Requisicao deve levantar OTRSAuthenticationError em erro 401."""

        def err401():
            return httpx.Response(
                status_code=401,
                text="Unauthorized",
                request=httpx.Request("POST", "http://test"),
            )

        mock_http = _setup_client_mock(client)
        mock_http.post.side_effect = [
            _session_response(),  # initial _create_session
            err401(),  # attempt 1: request fails 401
            _session_response(),  # retry: _create_session succeeds
            err401(),  # attempt 2: request fails 401
            _session_response(),  # retry: _create_session succeeds
            err401(),  # attempt 3: request fails 401
        ]

        with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(
                OTRSAuthenticationError, match="Credenciais OTRS invalidas"
            ):
                await client.request("TicketGet")

    @pytest.mark.asyncio
    async def test_request_raises_api_error_on_500(self, client: OTRSClient) -> None:
        """Requisicao deve levantar OTRSAPIError em erro 500."""

        def err500():
            return httpx.Response(
                status_code=500,
                text="Internal Server Error",
                request=httpx.Request("POST", "http://test"),
            )

        mock_http = _setup_client_mock(client)
        mock_http.post.side_effect = [
            _session_response(),  # initial _create_session
            err500(),  # attempt 1: request fails 500
            err500(),  # attempt 2: request fails 500 (no session invalidation on 500)
            err500(),  # attempt 3: request fails 500
        ]

        with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(OTRSAPIError, match="Erro HTTP 500"):
                await client.request("TicketGet")

    @pytest.mark.asyncio
    async def test_request_recreates_session_on_auth_fail(
        self, client: OTRSClient
    ) -> None:
        """Sessao expirada deve ser recriada automaticamente."""
        auth_fail_response = _mock_response(
            {
                "Error": {
                    "ErrorCode": "TicketSearch.AuthFail",
                    "ErrorMessage": "Session invalid",
                }
            }
        )

        mock_http = _setup_client_mock(
            client,
            _session_response(),
            auth_fail_response,
            _mock_response({"SessionID": "new-session-456"}),
            _mock_response({"TicketID": "123"}),
        )

        with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.request("TicketGet")

        assert result == {"TicketID": "123"}
        assert client._session_id == "new-session-456"


class TestOTRSClientGetTicket:
    """Testes para o metodo get_ticket."""

    @pytest.mark.asyncio
    async def test_get_ticket_success(self, client: OTRSClient) -> None:
        """get_ticket deve retornar dados do ticket."""
        _setup_client_mock(
            client,
            _session_response(),
            _mock_response({"TicketID": "123", "Title": "Test"}),
        )

        result = await client.get_ticket("123")

        assert result["TicketID"] == "123"
        assert "WebURL" in result
        assert "HistoryWebURL" in result


class TestOTRSClientCreateTicket:
    """Testes para o metodo create_ticket."""

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, client: OTRSClient) -> None:
        """create_ticket deve criar ticket e retornar dados."""
        _setup_client_mock(
            client, _session_response(), _mock_response({"TicketID": "456"})
        )

        result = await client.create_ticket("Test Title", "Test Body")

        assert result["TicketID"] == "456"
        assert "WebURL" in result


class TestOTRSClientSearchTickets:
    """Testes para o metodo search_tickets."""

    @pytest.mark.asyncio
    async def test_search_tickets_success(self, client: OTRSClient) -> None:
        """search_tickets deve retornar lista de tickets."""
        _setup_client_mock(
            client,
            _session_response(),
            _mock_response({"TicketID": ["123", "456"]}),
        )

        result = await client.search_tickets(limit=10)

        assert result["TicketID"] == ["123", "456"]
        assert "WebSearchURL" in result
        assert "TicketWebURLs" in result


class TestOTRSClientUpdateTicket:
    """Testes para o metodo update_ticket."""

    @pytest.mark.asyncio
    async def test_update_ticket_success(self, client: OTRSClient) -> None:
        """update_ticket deve atualizar ticket."""
        _setup_client_mock(
            client, _session_response(), _mock_response({"TicketID": "123"})
        )

        result = await client.update_ticket("123", title="New Title")

        assert result["TicketID"] == "123"
        assert "WebURL" in result


class TestOTRSClientGetTicketHistory:
    """Testes para o metodo get_ticket_history."""

    @pytest.mark.asyncio
    async def test_get_ticket_history_success(self, client: OTRSClient) -> None:
        """get_ticket_history deve retornar historico do ticket."""
        _setup_client_mock(
            client,
            _session_response(),
            _mock_response({"TicketID": "123", "History": []}),
        )

        result = await client.get_ticket_history("123")

        assert result["TicketID"] == "123"
        assert "WebURL" in result
        assert "HistoryWebURL" in result
