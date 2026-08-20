"""Testes para o modulo de configuracao."""

import os
from unittest.mock import patch

import pytest

from otrs_mcp.config import OTRSConfig
from otrs_mcp.exceptions import OTRSValidationError


class TestOTRSConfig:
    """Testes para a classe OTRSConfig."""

    def test_config_with_valid_env(self) -> None:
        """Configuracao com variaveis de ambiente validas."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs/nph-genericinterface.pl/Webservice/Test",
                "OTRS_USERNAME": "user",
                "OTRS_PASSWORD": "pass",
            },
        ):
            config = OTRSConfig()
            assert config.base_url == "https://otrs.example.com/otrs/nph-genericinterface.pl/Webservice/Test"
            assert config.username == "user"
            assert config.password == "pass"
            assert config.verify_ssl is False
            assert config.timeout == 30
            assert config.default_queue == "Raw"
            assert config.default_state == "new"
            assert config.default_priority == "3 normal"
            assert config.default_type == "Unclassified"

    def test_config_missing_base_url(self) -> None:
        """Configuracao sem OTRS_BASE_URL deve levantar erro."""
        with patch.dict(
            os.environ,
            {
                "OTRS_USERNAME": "user",
                "OTRS_PASSWORD": "pass",
            },
            clear=True,
        ):
            with pytest.raises(OTRSValidationError, match="OTRS_BASE_URL"):
                OTRSConfig()

    def test_config_missing_username(self) -> None:
        """Configuracao sem OTRS_USERNAME deve levantar erro."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs",
                "OTRS_PASSWORD": "pass",
            },
            clear=True,
        ):
            with pytest.raises(OTRSValidationError, match="OTRS_USERNAME"):
                OTRSConfig()

    def test_config_missing_password(self) -> None:
        """Configuracao sem OTRS_PASSWORD deve levantar erro."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs",
                "OTRS_USERNAME": "user",
            },
            clear=True,
        ):
            with pytest.raises(OTRSValidationError, match="OTRS_PASSWORD"):
                OTRSConfig()

    def test_config_missing_all_required(self) -> None:
        """Configuracao sem nenhuma variavel obrigatoria deve levantar erro."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(OTRSValidationError, match="OTRS_BASE_URL, OTRS_USERNAME, OTRS_PASSWORD"):
                OTRSConfig()

    def test_config_web_base_url_derived(self) -> None:
        """web_base_url deve ser derivado de base_url."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs/nph-genericinterface.pl/Webservice/Test",
                "OTRS_USERNAME": "user",
                "OTRS_PASSWORD": "pass",
            },
        ):
            config = OTRSConfig()
            assert config.web_base_url == "https://otrs.example.com/otrs"

    def test_config_web_base_url_explicit(self) -> None:
        """web_base_url explicita nao deve ser sobrescrita."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs/nph-genericinterface.pl/Webservice/Test",
                "OTRS_USERNAME": "user",
                "OTRS_PASSWORD": "pass",
                "OTRS_WEB_BASE_URL": "https://custom.example.com/otrs",
            },
        ):
            config = OTRSConfig()
            assert config.web_base_url == "https://custom.example.com/otrs"

    def test_config_verify_ssl_true(self) -> None:
        """OTRS_VERIFY_SSL=true deve ativar verificacao SSL."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs",
                "OTRS_USERNAME": "user",
                "OTRS_PASSWORD": "pass",
                "OTRS_VERIFY_SSL": "true",
            },
        ):
            config = OTRSConfig()
            assert config.verify_ssl is True

    def test_config_timeout_custom(self) -> None:
        """OTRS_TIMEOUT deve ser respeitado."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs",
                "OTRS_USERNAME": "user",
                "OTRS_PASSWORD": "pass",
                "OTRS_TIMEOUT": "60",
            },
        ):
            config = OTRSConfig()
            assert config.timeout == 60

    def test_get_ticket_web_url(self) -> None:
        """get_ticket_web_url deve retornar URL correta."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs/nph-genericinterface.pl/Webservice/Test",
                "OTRS_USERNAME": "user",
                "OTRS_PASSWORD": "pass",
            },
        ):
            config = OTRSConfig()
            url = config.get_ticket_web_url("123")
            assert url == "https://otrs.example.com/otrs/index.pl?Action=AgentTicketZoom;TicketID=123"

    def test_get_ticket_history_web_url(self) -> None:
        """get_ticket_history_web_url deve retornar URL correta."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs/nph-genericinterface.pl/Webservice/Test",
                "OTRS_USERNAME": "user",
                "OTRS_PASSWORD": "pass",
            },
        ):
            config = OTRSConfig()
            url = config.get_ticket_history_web_url("456")
            assert url == "https://otrs.example.com/otrs/index.pl?Action=AgentTicketHistory;TicketID=456"

    def test_get_ticket_search_web_url(self) -> None:
        """get_ticket_search_web_url deve retornar URL correta."""
        with patch.dict(
            os.environ,
            {
                "OTRS_BASE_URL": "https://otrs.example.com/otrs/nph-genericinterface.pl/Webservice/Test",
                "OTRS_USERNAME": "user",
                "OTRS_PASSWORD": "pass",
            },
        ):
            config = OTRSConfig()
            url = config.get_ticket_search_web_url()
            assert url == "https://otrs.example.com/otrs/index.pl?Action=AgentTicketSearch"
