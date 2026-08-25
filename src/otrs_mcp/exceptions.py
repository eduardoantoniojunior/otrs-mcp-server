"""Excecoes customizadas para o OTRS MCP Server."""


class OTRSError(Exception):
    """Excecao base para erros do OTRS."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class OTRSConnectionError(OTRSError):
    """Erro de conexao com o OTRS."""


class OTRSAuthenticationError(OTRSError):
    """Erro de autenticacao no OTRS."""


class OTRSTicketNotFoundError(OTRSError):
    """Ticket nao encontrado no OTRS."""


class OTRSValidationError(OTRSError):
    """Erro de validacao de dados enviados ao OTRS."""


class OTRSAPIError(OTRSError):
    """Erro retornado pela API do OTRS."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
