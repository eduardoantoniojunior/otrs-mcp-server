"""Fixtures compartilhadas para testes do OTRS MCP Server."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.tools import init_tools


@pytest.fixture
def otrs_config() -> OTRSConfig:
    """Configuracao OTRS para testes."""
    with patch.dict(
        os.environ,
        {
            "OTRS_BASE_URL": "https://test-otrs.example.com/otrs/nph-genericinterface.pl/Webservice/Test",
            "OTRS_USERNAME": "test_user",
            "OTRS_PASSWORD": "test_pass",
            "OTRS_VERIFY_SSL": "false",
            "OTRS_TIMEOUT": "10",
            "OTRS_DEFAULT_QUEUE": "Raw",
            "OTRS_DEFAULT_STATE": "new",
            "OTRS_DEFAULT_PRIORITY": "3 normal",
            "OTRS_DEFAULT_TYPE": "Unclassified",
        },
    ):
        return OTRSConfig()


@pytest.fixture
def otrs_client(otrs_config: OTRSConfig) -> OTRSClient:
    """Cliente OTRS para testes."""
    return OTRSClient(otrs_config)


@pytest.fixture
def mock_client() -> AsyncMock:
    """Cliente OTRS mockado para testes de tools/resources."""
    client = AsyncMock(spec=OTRSClient)
    client.get_ticket.return_value = {
        "TicketID": "123",
        "Title": "Test Ticket",
        "State": "new",
        "Priority": "3 normal",
        "WebURL": "https://test-otrs.example.com/index.pl?Action=AgentTicketZoom;TicketID=123",
        "HistoryWebURL": "https://test-otrs.example.com/index.pl?Action=AgentTicketHistory;TicketID=123",
    }
    client.create_ticket.return_value = {
        "TicketID": "456",
        "WebURL": "https://test-otrs.example.com/index.pl?Action=AgentTicketZoom;TicketID=456",
    }
    client.search_tickets.return_value = {
        "TicketID": ["123", "456"],
        "WebSearchURL": "https://test-otrs.example.com/index.pl?Action=AgentTicketSearch",
        "TicketWebURLs": [
            {
                "TicketID": "123",
                "WebURL": "https://test-otrs.example.com/index.pl?Action=AgentTicketZoom;TicketID=123",
            },
            {
                "TicketID": "456",
                "WebURL": "https://test-otrs.example.com/index.pl?Action=AgentTicketZoom;TicketID=456",
            },
        ],
    }
    client.update_ticket.return_value = {
        "TicketID": "123",
        "WebURL": "https://test-otrs.example.com/index.pl?Action=AgentTicketZoom;TicketID=123",
    }
    client.get_ticket_history.return_value = {
        "TicketID": "123",
        "History": [{"ArticleID": "1", "Name": "Ticket created"}],
        "WebURL": "https://test-otrs.example.com/index.pl?Action=AgentTicketZoom;TicketID=123",
        "HistoryWebURL": "https://test-otrs.example.com/index.pl?Action=AgentTicketHistory;TicketID=123",
    }
    return client


@pytest.fixture
def initialized_tools(otrs_config: OTRSConfig, mock_client: AsyncMock) -> None:
    """Inicializa tools com client mockado."""
    init_tools(otrs_config, mock_client)
