"""Configuracao do OTRS MCP Server."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from otrs_mcp.exceptions import OTRSValidationError


class OTRSConfig(BaseSettings):
    """Configuracao do OTRS carregada de variaveis de ambiente."""

    model_config = SettingsConfigDict(env_prefix="OTRS_")

    base_url: str = ""
    username: str = ""
    password: str = ""
    verify_ssl: bool = True
    timeout: int = 30
    debug: bool = False
    default_queue: str = "Raw"
    default_state: str = "new"
    default_priority: str = "3 normal"
    default_type: str = ""
    web_base_url: str = ""
    valid_queues: str = ""
    valid_types: str = ""

    def model_post_init(self, __context: object) -> None:
        missing = []
        if not self.base_url:
            missing.append("OTRS_BASE_URL")
        if not self.username:
            missing.append("OTRS_USERNAME")
        if not self.password:
            missing.append("OTRS_PASSWORD")
        if missing:
            raise OTRSValidationError(
                f"Variaveis de ambiente obrigatorias nao configuradas: {', '.join(missing)}"
            )
        if not self.web_base_url:
            # Extrai a base web a partir da URL da API.
            # Ex: "https://host/otrs/nph-genericinterface.pl/Webservice/X"
            #   → "https://host/otrs"
            base = self.base_url.split("/nph-genericinterface.pl", 1)[0]
            self.web_base_url = base.rstrip("/")
        else:
            self.web_base_url = self.web_base_url.rstrip("/")

    def get_ticket_web_url(self, ticket_id: str) -> str:
        return (
            f"{self.web_base_url}/index.pl?Action=AgentTicketZoom;TicketID={ticket_id}"
        )

    def get_ticket_history_web_url(self, ticket_id: str) -> str:
        return f"{self.web_base_url}/index.pl?Action=AgentTicketHistory;TicketID={ticket_id}"

    def get_ticket_search_web_url(self) -> str:
        return f"{self.web_base_url}/index.pl?Action=AgentTicketSearch"
