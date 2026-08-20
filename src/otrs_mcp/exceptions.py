"""Excecoes customizadas para o OTRS MCP Server."""


class OTRError(Exception):
    """Excecao base para erros do OTRS."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class OTRSConnectionError(OTRError):
    """Erro de conexao com o OTRS."""


class OTRSAuthenticationError(OTRError):
    """Erro de autenticacao no OTRS."""


class OTRSTicketNotFoundError(OTRError):
    """Ticket nao encontrado no OTRS."""


class OTRSValidationError(OTRError):
    """Erro de validacao de dados enviados ao OTRS."""


class OTRSAPIError(OTRError):
    """Erro retornado pela API do OTRS."""

    def __init__(
        self, message: str, status_code: int | None = None, response_body: str | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
