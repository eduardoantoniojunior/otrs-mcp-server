"""Testes para as tools MCP."""

import pytest

from otrs_mcp.exceptions import OTRSValidationError
from otrs_mcp.tools import (
    create_ticket,
    get_ticket,
    get_ticket_history,
    search_tickets,
    update_ticket,
)


class TestCreateTicket:
    """Testes para a tool create_ticket."""

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, initialized_tools, mock_client) -> None:
        """create_ticket deve chamar client.create_ticket com parametros corretos."""
        result = await create_ticket(title="Test", body="Body")

        mock_client.create_ticket.assert_called_once_with(
            title="Test",
            body="Body",
            queue="Raw",
            priority="3 normal",
            state=None,
            customer_user=None,
            ticket_type=None,
        )
        assert result["TicketID"] == "456"

    @pytest.mark.asyncio
    async def test_create_ticket_with_custom_params(
        self, initialized_tools, mock_client
    ) -> None:
        """create_ticket deve aceitar parametros customizados."""
        await create_ticket(
            title="Test",
            body="Body",
            queue="Junk",
            priority="4 high",
            state="open",
            customer_user="customer@example.com",
            ticket_type="Incident",
        )

        mock_client.create_ticket.assert_called_once_with(
            title="Test",
            body="Body",
            queue="Junk",
            priority="4 high",
            state="open",
            customer_user="customer@example.com",
            ticket_type="Incident",
        )

    @pytest.mark.asyncio
    async def test_create_ticket_invalid_priority(
        self, initialized_tools, mock_client
    ) -> None:
        """create_ticket deve rejeitar prioridade invalida."""
        with pytest.raises(OTRSValidationError, match="Prioridade invalida"):
            await create_ticket(title="Test", body="Body", priority="invalid")

        mock_client.create_ticket.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_ticket_invalid_queue_raises(
        self, initialized_tools, mock_client
    ) -> None:
        """create_ticket deve rejeitar fila invalida."""
        with pytest.raises(OTRSValidationError, match="Fila invalida"):
            await create_ticket(title="Test", body="Body", queue="InvalidQueue")

        mock_client.create_ticket.assert_not_called()


class TestGetTicket:
    """Testes para a tool get_ticket."""

    @pytest.mark.asyncio
    async def test_get_ticket_success(self, initialized_tools, mock_client) -> None:
        """get_ticket deve chamar client.get_ticket."""
        result = await get_ticket(ticket_id="123")

        mock_client.get_ticket.assert_called_once_with(
            ticket_id="123",
            include_dynamic_fields=True,
            include_extended_data=True,
        )
        assert result["TicketID"] == "123"

    @pytest.mark.asyncio
    async def test_get_ticket_without_dynamic_fields(
        self, initialized_tools, mock_client
    ) -> None:
        """get_ticket deve aceitar flag include_dynamic_fields=False."""
        await get_ticket(ticket_id="123", include_dynamic_fields=False)

        mock_client.get_ticket.assert_called_once_with(
            ticket_id="123",
            include_dynamic_fields=False,
            include_extended_data=True,
        )


class TestSearchTickets:
    """Testes para a tool search_tickets."""

    @pytest.mark.asyncio
    async def test_search_tickets_success(self, initialized_tools, mock_client) -> None:
        """search_tickets deve chamar client.search_tickets."""
        result = await search_tickets(limit=10)

        mock_client.search_tickets.assert_called_once_with(
            customer_user=None,
            queue=None,
            state=None,
            priority=None,
            title=None,
            limit=10,
            sort_by="Age",
            order_by="Down",
        )
        assert "TicketID" in result

    @pytest.mark.asyncio
    async def test_search_tickets_with_filters(
        self, initialized_tools, mock_client
    ) -> None:
        """search_tickets deve aceitar filtros."""
        await search_tickets(
            customer_user="user@test.com",
            queue="Raw",
            state="open",
            priority="3 normal",
            title="Test",
        )

        mock_client.search_tickets.assert_called_once_with(
            customer_user="user@test.com",
            queue="Raw",
            state="open",
            priority="3 normal",
            title="Test",
            limit=50,
            sort_by="Age",
            order_by="Down",
        )


class TestUpdateTicket:
    """Testes para a tool update_ticket."""

    @pytest.mark.asyncio
    async def test_update_ticket_success(self, initialized_tools, mock_client) -> None:
        """update_ticket deve chamar client.update_ticket."""
        result = await update_ticket(ticket_id="123", title="New Title")

        mock_client.update_ticket.assert_called_once_with(
            ticket_id="123",
            title="New Title",
            queue=None,
            priority=None,
            state=None,
            customer_user=None,
            owner=None,
        )
        assert result["TicketID"] == "123"

    @pytest.mark.asyncio
    async def test_update_ticket_invalid_priority(
        self, initialized_tools, mock_client
    ) -> None:
        """update_ticket deve rejeitar prioridade invalida."""
        with pytest.raises(OTRSValidationError, match="Prioridade invalida"):
            await update_ticket(ticket_id="123", priority="invalid")

        mock_client.update_ticket.assert_not_called()


class TestGetTicketHistory:
    """Testes para a tool get_ticket_history."""

    @pytest.mark.asyncio
    async def test_get_ticket_history_success(
        self, initialized_tools, mock_client
    ) -> None:
        """get_ticket_history deve chamar client.get_ticket_history."""
        result = await get_ticket_history(ticket_id="123")

        mock_client.get_ticket_history.assert_called_once_with(ticket_id="123")
        assert "History" in result
