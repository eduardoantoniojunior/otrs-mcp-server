"""Autenticacao por API key para o transporte HTTP do servidor MCP.

O SDK `mcp` valida bearer tokens atraves do protocolo `TokenVerifier`:

- `BearerAuthBackend` le o header `Authorization: Bearer <token>` e chama
  `verify_token()`. Retornar `None` marca a requisicao como nao autenticada.
- `RequireAuthMiddleware` embrulha a rota do streamable-http e responde
  `401` quando nao ha identidade autenticada, ou `403` quando falta um
  escopo obrigatorio.

Aqui as API keys ja existentes (`sk-otrs-...`, tabela `api_keys`) sao usadas
como bearer token, e as permissoes da key (`read`, `write`, `admin`) viram
escopos OAuth. Assim o MCP passa a exigir credencial valida, com o mesmo
cadastro e as mesmas permissoes da API REST.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

from otrs_mcp.database import check_rate_limit, verify_api_key
from otrs_mcp.exceptions import OTRSPermissionError

logger = logging.getLogger(__name__)

# Escopos exigidos globalmente na rota MCP. Vazio = basta um token valido;
# a permissao fina (read/write) e verificada por tool em `require_scope()`.
REQUIRED_SCOPES: list[str] = []


def auth_enabled() -> bool:
    """Indica se a autenticacao do MCP deve ser aplicada.

    Somente o transporte HTTP carrega headers. Em `stdio` o processo e' iniciado
    localmente pelo proprio cliente, que ja possui as credenciais do OTRS no
    ambiente, portanto nao ha token a exigir.
    """
    return os.getenv("OTRS_MCP_TRANSPORT", "stdio").lower() == "http"


class ApiKeyVerifier(TokenVerifier):
    """Valida uma API key do OTRS MCP como bearer token."""

    async def verify_token(self, token: str) -> AccessToken | None:
        # `verify_api_key` e' sincrono (SQLite); roda em thread para nao
        # bloquear o event loop do servidor.
        identity = await asyncio.to_thread(verify_api_key, token)

        if identity is None:
            logger.warning("MCP: token rejeitado (invalido, revogado ou expirado)")
            return None

        key_id = identity["id"]
        agent_name = identity.get("agent_name") or "unknown"
        permissions = identity.get("permissions") or []
        rate_limit = identity.get("rate_limit", 0) or 0

        # Rate limit por key, mesmo criterio da API REST.
        if rate_limit > 0:
            allowed, current = await asyncio.to_thread(
                check_rate_limit, key_id, rate_limit
            )
            if not allowed:
                # O protocolo TokenVerifier so permite aceitar ou recusar, logo
                # o excesso e' reportado como 401 e nao como 429.
                logger.warning(
                    "MCP: rate limit excedido para key id=%s agent=%s (%d/%d por minuto)",
                    key_id,
                    agent_name,
                    current,
                    rate_limit,
                )
                return None

        logger.info("MCP: token aceito para agent=%s (key id=%s)", agent_name, key_id)

        return AccessToken(
            token=token,
            client_id=f"otrs-key-{key_id}",
            scopes=list(permissions),
            subject=agent_name,
            claims={
                "key_id": key_id,
                "name": identity.get("name"),
                "agent_name": agent_name,
                "rate_limit": rate_limit,
            },
        )


def build_auth_settings() -> AuthSettings:
    """Monta as AuthSettings exigidas pelo FastMCP quando ha token_verifier.

    `resource_server_url=None` evita publicar as rotas de metadados OAuth
    Protected Resource: a autenticacao aqui e' por API key emitida pelo proprio
    painel, nao por um authorization server OAuth externo.
    """
    issuer_url = os.getenv("OTRS_MCP_ISSUER_URL") or "https://otrs-mcp.local"
    return AuthSettings(
        issuer_url=issuer_url,  # type: ignore[arg-type]
        resource_server_url=None,
        required_scopes=REQUIRED_SCOPES,
    )


def current_identity() -> dict[str, Any] | None:
    """Retorna a identidade autenticada da requisicao MCP atual, se houver."""
    from mcp.server.auth.middleware.auth_context import get_access_token

    access_token = get_access_token()
    if access_token is None:
        return None

    claims = access_token.claims or {}
    return {
        "key_id": claims.get("key_id"),
        "name": claims.get("name"),
        "agent_name": claims.get("agent_name") or access_token.subject,
        "permissions": list(access_token.scopes),
        "rate_limit": claims.get("rate_limit", 0),
    }


def _in_mcp_request() -> bool:
    """Indica se a execucao atual esta dentro de uma requisicao MCP.

    Distingue uma chamada vinda de um cliente MCP de uma chamada direta a
    funcao em processo (testes, reuso interno). Sem requisicao nao existe
    credencial a exigir, e a barreira de rede ja foi aplicada antes.
    """
    from mcp.server.lowlevel.server import request_ctx

    try:
        request_ctx.get()
        return True
    except LookupError:
        return False


def require_scope(scope: str) -> dict[str, Any] | None:
    """Exige que a requisicao MCP atual tenha a permissao informada.

    Retorna a identidade quando autorizada e levanta `OTRSPermissionError`
    quando o token nao possui a permissao.

    A verificacao e' dispensada quando a autenticacao esta desligada
    (transporte stdio) ou quando nao ha requisicao MCP em curso. No transporte
    HTTP quem barra requisicoes sem credencial e' o `RequireAuthMiddleware`,
    antes de qualquer tool executar; esta funcao adiciona a checagem fina de
    permissao (read/write) sobre um token que ja foi validado.
    """
    if not auth_enabled():
        return None

    if not _in_mcp_request():
        return None

    identity = current_identity()
    if identity is None:
        # Requisicao MCP sem identidade: falha fechada.
        raise OTRSPermissionError(
            "Autenticacao necessaria: envie uma API key valida em "
            "'Authorization: Bearer sk-otrs-...'"
        )

    permissions = identity.get("permissions", [])
    if scope not in permissions and "admin" not in permissions:
        raise OTRSPermissionError(
            f"Permissao '{scope}' necessaria. A API key possui: "
            f"{', '.join(permissions) or 'nenhuma'}"
        )

    return identity
