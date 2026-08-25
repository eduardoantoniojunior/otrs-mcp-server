"""Testes para os resources MCP."""

import json

import pytest

from otrs_mcp.resources import (
    search_tickets_resource,
    ticket_history_resource,
    ticket_resource,
)


class TestTicketResource:
    """Testes para o resource ticket_resource."""

    @pytest.mark.asyncio
    async def test_ticket_resource_success(
        self, initialized_tools, mock_client
    ) -> None:
        """ticket_resource deve retornar JSON do ticket."""
        result = await ticket_resource(ticket_id="123")

        mock_client.get_ticket.assert_called_once_with(ticket_id="123")
        data = json.loads(result)
        assert data["TicketID"] == "123"
        assert data["Title"] == "Test Ticket"

    @pytest.mark.asyncio
    async def test_ticket_resource_error(self, initialized_tools, mock_client) -> None:
        """ticket_resource deve tratar erros."""
        mock_client.get_ticket.side_effect = Exception("Connection error")

        result = await ticket_resource(ticket_id="123")

        assert "Error retrieving ticket" in result
        mock_client.get_ticket.side_effect = None


class TestTicketHistoryResource:
    """Testes para o resource ticket_history_resource."""

    @pytest.mark.asyncio
    async def test_ticket_history_resource_success(
        self, initialized_tools, mock_client
    ) -> None:
        """ticket_history_resource deve retornar JSON do historico."""
        result = await ticket_history_resource(ticket_id="123")

        mock_client.get_ticket_history.assert_called_once_with(ticket_id="123")
        data = json.loads(result)
        assert data["TicketID"] == "123"
        assert "History" in data

    @pytest.mark.asyncio
    async def test_ticket_history_resource_error(
        self, initialized_tools, mock_client
    ) -> None:
        """ticket_history_resource deve tratar erros."""
        mock_client.get_ticket_history.side_effect = Exception("Connection error")

        result = await ticket_history_resource(ticket_id="123")

        assert "Error retrieving ticket history" in result
        mock_client.get_ticket_history.side_effect = None


class TestSearchTicketsResource:
    """Testes para o resource search_tickets_resource."""

    @pytest.mark.asyncio
    async def test_search_tickets_resource_success(
        self, initialized_tools, mock_client
    ) -> None:
        """search_tickets_resource deve retornar JSON dos tickets."""
        result = await search_tickets_resource()

        mock_client.search_tickets.assert_called_once_with(limit=20)
        data = json.loads(result)
        assert "TicketID" in data

    @pytest.mark.asyncio
    async def test_search_tickets_resource_error(
        self, initialized_tools, mock_client
    ) -> None:
        """search_tickets_resource deve tratar erros."""
        mock_client.search_tickets.side_effect = Exception("Connection error")

        result = await search_tickets_resource()

        assert "Error searching tickets" in result
        mock_client.search_tickets.side_effect = None
