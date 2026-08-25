"""Modulo de autenticacao para o OTRS MCP Server.

Fornece JWT para o frontend (admin login) e verificacao de API key para agentes.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from otrs_mcp.database import verify_admin_user, verify_api_key

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

JWT_SECRET = os.getenv("OTRS_JWT_SECRET", "change-me-in-production-use-a-real-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("OTRS_JWT_EXPIRE_MINUTES", "480"))  # 8 hours

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# JWT Helpers
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: int, username: str, expires_delta: timedelta | None = None
) -> str:
    """Gera um token JWT para o usuario admin."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
        "type": "admin",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica e valida um token JWT. Levanta excecao se invalido."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        )


# ---------------------------------------------------------------------------
# FastAPI Dependencies
# ---------------------------------------------------------------------------

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """Dependency que valida JWT e retorna o usuario admin autenticado."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticacao necessario",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if payload.get("type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: token nao e de administrador",
        )
    return {
        "user_id": int(payload["sub"]),
        "username": payload["username"],
    }


async def get_api_key_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """Dependency que valida API key (X-API-Key header ou Bearer token) e retorna a identidade do agente."""
    api_key = None

    # Tentar via Bearer token (para agentes que usam Authorization header)
    if credentials:
        api_key = credentials.credentials

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key necessaria (header X-API-Key ou Authorization: Bearer)",
        )

    identity = verify_api_key(api_key)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key invalida, inativa ou expirada",
        )

    return identity


def require_permission(permission: str):
    """Factory de dependency que verifica se a API key tem uma permissao especifica."""

    async def _check(
        identity: dict[str, Any] = Depends(get_api_key_identity),
    ) -> dict[str, Any]:
        perms = identity.get("permissions", [])
        if permission not in perms and "admin" not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissao '{permission}' necessaria",
            )
        return identity

    return _check
