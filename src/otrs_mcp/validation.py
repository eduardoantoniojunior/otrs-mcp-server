"""Validacoes compartilhadas do OTRS MCP Server."""

import re

from otrs_mcp.exceptions import OTRSValidationError

# Regex para validar ticket_id (apenas numeros, 1-20 digitos)
TICKET_ID_PATTERN = re.compile(r"^\d{1,20}$")


def validate_ticket_id(ticket_id: str) -> str:
    """Valida que ticket_id contem apenas digitos (1-20).

    Retorna o ticket_id se valido, caso contrario levanta OTRSValidationError.
    Usado tanto pela API REST quanto pelas tools MCP.
    """
    if not TICKET_ID_PATTERN.match(ticket_id):
        raise OTRSValidationError(
            f"ticket_id invalido: '{ticket_id}'. Deve conter apenas digitos (1-20)."
        )
    return ticket_id
