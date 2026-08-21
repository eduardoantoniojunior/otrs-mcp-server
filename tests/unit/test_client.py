"""Testes para o cliente HTTP do OTRS."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from otrs_mcp.client import OTRSClient, MAX_RETRIES
from otrs_mcp.config import OTRSConfig
from otrs_mcp.exceptions import OTRSAPIError, OTRSAuthenticationError, OTRSConnectionError


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


def _session_response() -> httpx.Response:
    """Cria uma resposta mockada de SessionCreate."""
    return _mock_response({"SessionID": "test-session-id-123"})


def _mock_client_with_session(*responses: httpx.Response) -> AsyncMock:
    """Cria um httpx client mockado que retorna session + respostas."""
    mock_client = AsyncMock()
    mock_client.post.side_effect = [_session_response(), *responses]
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestOTRSClientRequest:
    """Testes para o metodo request do OTRSClient."""

    @pytest.mark.asyncio
    async def test_request_success(self, client: OTRSClient) -> None:
        """Requisicao bem-sucedida deve retornar dados."""
        mock_client = _mock_client_with_session(_mock_response({"TicketID": "123"}))

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await client.request("TicketGet", {"TicketID": "123"})

            assert result == {"TicketID": "123"}
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_request_includes_auth(self, client: OTRSClient) -> None:
        """Requisicao deve incluir CustomerUserLogin, Password e SessionID."""
        mock_client = _mock_client_with_session(_mock_response({}))

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            await client.request("TicketGet")

            session_call = mock_client.post.call_args_list[0]
            session_json = session_call.kwargs.get("json") or session_call[1].get("json")
            assert session_json["CustomerUserLogin"] == "user"
            assert session_json["Password"] == "pass"
            assert "SessionID" not in session_json

            request_call = mock_client.post.call_args_list[1]
            request_json = request_call.kwargs.get("json") or request_call[1].get("json")
            assert request_json["CustomerUserLogin"] == "user"
            assert request_json["Password"] == "pass"
            assert request_json["SessionID"] == "test-session-id-123"

    @pytest.mark.asyncio
    async def test_request_reuses_session(self, client: OTRSClient) -> None:
        """Sessao criada uma vez deve ser reutilizada."""
        mock_client = _mock_client_with_session(
            _mock_response({"TicketID": "1"}),
            _mock_response({"TicketID": "2"}),
        )

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            await client.request("TicketGet", {"TicketID": "1"})
            await client.request("TicketGet", {"TicketID": "2"})

            assert mock_client.post.call_count == 3

            first_call_json = mock_client.post.call_args_list[0].kwargs.get("json")
            assert "SessionID" not in first_call_json

            second_call_json = mock_client.post.call_args_list[1].kwargs.get("json")
            assert second_call_json["SessionID"] == "test-session-id-123"

            third_call_json = mock_client.post.call_args_list[2].kwargs.get("json")
            assert third_call_json["SessionID"] == "test-session-id-123"

    @pytest.mark.asyncio
    async def test_request_retry_on_http_error(self, client: OTRSClient) -> None:
        """Requisicao deve retry em caso de erro HTTP."""
        error_response = httpx.Response(status_code=500, text="Server Error")
        error_response.raise_for_status = lambda: (_ for _ in ()).throw(
            httpx.HTTPStatusError("Server Error", request=httpx.Request("POST", "http://test"), response=error_response)
        )

        success_response = _mock_response({"TicketID": "123"})

        mock_client = AsyncMock()
        mock_client.post.side_effect = [_session_response(), error_response, success_response]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
                result = await client.request("TicketGet")

            assert result == {"TicketID": "123"}
            assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_request_raises_connection_error_after_retries(self, client: OTRSClient) -> None:
        """Requisicao deve levantar OTRSConnectionError apos falhas de conexao."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_session_client = AsyncMock()
        mock_session_client.post.return_value = _session_response()
        mock_session_client.__aenter__ = AsyncMock(return_value=mock_session_client)
        mock_session_client.__aexit__ = AsyncMock(return_value=False)

        call_count = [0]

        def client_factory(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_session_client
            return mock_client

        with patch("otrs_mcp.client.httpx.AsyncClient", side_effect=client_factory):
            with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(OTRSConnectionError, match="Falha apos"):
                    await client.request("TicketGet")

    @pytest.mark.asyncio
    async def test_request_raises_auth_error_on_401(self, client: OTRSClient) -> None:
        """Requisicao deve levantar OTRSAuthenticationError em erro 401."""
        error_response = httpx.Response(status_code=401, text="Unauthorized")
        error_response.raise_for_status = lambda: (_ for _ in ()).throw(
            httpx.HTTPStatusError("Unauthorized", request=httpx.Request("POST", "http://test"), response=error_response)
        )

        success_session_1 = AsyncMock()
        success_session_1.post.return_value = _session_response()
        success_session_1.__aenter__ = AsyncMock(return_value=success_session_1)
        success_session_1.__aexit__ = AsyncMock(return_value=False)

        error_client_1 = AsyncMock()
        error_client_1.post.return_value = error_response
        error_client_1.__aenter__ = AsyncMock(return_value=error_client_1)
        error_client_1.__aexit__ = AsyncMock(return_value=False)

        success_session_2 = AsyncMock()
        success_session_2.post.return_value = _session_response()
        success_session_2.__aenter__ = AsyncMock(return_value=success_session_2)
        success_session_2.__aexit__ = AsyncMock(return_value=False)

        error_client_2 = AsyncMock()
        error_client_2.post.return_value = error_response
        error_client_2.__aenter__ = AsyncMock(return_value=error_client_2)
        error_client_2.__aexit__ = AsyncMock(return_value=False)

        success_session_3 = AsyncMock()
        success_session_3.post.return_value = _session_response()
        success_session_3.__aenter__ = AsyncMock(return_value=success_session_3)
        success_session_3.__aexit__ = AsyncMock(return_value=False)

        error_client_3 = AsyncMock()
        error_client_3.post.return_value = error_response
        error_client_3.__aenter__ = AsyncMock(return_value=error_client_3)
        error_client_3.__aexit__ = AsyncMock(return_value=False)

        clients = [
            success_session_1, error_client_1,
            success_session_2, error_client_2,
            success_session_3, error_client_3,
        ]
        call_count = [0]

        def client_factory(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return clients[idx]

        with patch("otrs_mcp.client.httpx.AsyncClient", side_effect=client_factory):
            with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(OTRSAuthenticationError, match="Credenciais OTRS invalidas"):
                    await client.request("TicketGet")

    @pytest.mark.asyncio
    async def test_request_raises_api_error_on_500(self, client: OTRSClient) -> None:
        """Requisicao deve levantar OTRSAPIError em erro 500."""
        error_response = httpx.Response(status_code=500, text="Internal Server Error")
        error_response.raise_for_status = lambda: (_ for _ in ()).throw(
            httpx.HTTPStatusError("Server Error", request=httpx.Request("POST", "http://test"), response=error_response)
        )

        success_session = AsyncMock()
        success_session.post.return_value = _session_response()
        success_session.__aenter__ = AsyncMock(return_value=success_session)
        success_session.__aexit__ = AsyncMock(return_value=False)

        error_client = AsyncMock()
        error_client.post.return_value = error_response
        error_client.__aenter__ = AsyncMock(return_value=error_client)
        error_client.__aexit__ = AsyncMock(return_value=False)

        call_count = [0]

        def client_factory(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return success_session
            return error_client

        with patch("otrs_mcp.client.httpx.AsyncClient", side_effect=client_factory):
            with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(OTRSAPIError, match="Erro HTTP 500"):
                    await client.request("TicketGet")

    @pytest.mark.asyncio
    async def test_request_recreates_session_on_auth_fail(self, client: OTRSClient) -> None:
        """Sessao expirada deve ser recriada automaticamente."""
        auth_fail_response = _mock_response({
            "Error": {
                "ErrorCode": "TicketSearch.AuthFail",
                "ErrorMessage": "Session invalid",
            }
        })
        success_response = _mock_response({"TicketID": "123"})

        mock_client = AsyncMock()
        mock_client.post.side_effect = [
            _session_response(),
            auth_fail_response,
            _mock_response({"SessionID": "new-session-456"}),
            success_response,
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            with patch("otrs_mcp.client.asyncio.sleep", new_callable=AsyncMock):
                result = await client.request("TicketGet")

            assert result == {"TicketID": "123"}
            assert client._session_id == "new-session-456"


class TestOTRSClientGetTicket:
    """Testes para o metodo get_ticket."""

    @pytest.mark.asyncio
    async def test_get_ticket_success(self, client: OTRSClient) -> None:
        """get_ticket deve retornar dados do ticket."""
        mock_client = _mock_client_with_session(
            _mock_response({"TicketID": "123", "Title": "Test"})
        )

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await client.get_ticket("123")

            assert result["TicketID"] == "123"
            assert "WebURL" in result
            assert "HistoryWebURL" in result


class TestOTRSClientCreateTicket:
    """Testes para o metodo create_ticket."""

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, client: OTRSClient) -> None:
        """create_ticket deve criar ticket e retornar dados."""
        mock_client = _mock_client_with_session(
            _mock_response({"TicketID": "456"})
        )

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await client.create_ticket("Test Title", "Test Body")

            assert result["TicketID"] == "456"
            assert "WebURL" in result


class TestOTRSClientSearchTickets:
    """Testes para o metodo search_tickets."""

    @pytest.mark.asyncio
    async def test_search_tickets_success(self, client: OTRSClient) -> None:
        """search_tickets deve retornar lista de tickets."""
        mock_client = _mock_client_with_session(
            _mock_response({"TicketID": ["123", "456"]})
        )

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await client.search_tickets(limit=10)

            assert result["TicketID"] == ["123", "456"]
            assert "WebSearchURL" in result
            assert "TicketWebURLs" in result


class TestOTRSClientUpdateTicket:
    """Testes para o metodo update_ticket."""

    @pytest.mark.asyncio
    async def test_update_ticket_success(self, client: OTRSClient) -> None:
        """update_ticket deve atualizar ticket."""
        mock_client = _mock_client_with_session(
            _mock_response({"TicketID": "123"})
        )

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await client.update_ticket("123", title="New Title")

            assert result["TicketID"] == "123"
            assert "WebURL" in result


class TestOTRSClientGetTicketHistory:
    """Testes para o metodo get_ticket_history."""

    @pytest.mark.asyncio
    async def test_get_ticket_history_success(self, client: OTRSClient) -> None:
        """get_ticket_history deve retornar historico do ticket."""
        mock_client = _mock_client_with_session(
            _mock_response({"TicketID": "123", "History": []})
        )

        with patch("otrs_mcp.client.httpx.AsyncClient", return_value=mock_client):
            result = await client.get_ticket_history("123")

            assert result["TicketID"] == "123"
            assert "WebURL" in result
            assert "HistoryWebURL" in result
