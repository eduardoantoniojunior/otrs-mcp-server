"""Rotas de autenticacao e gerenciamento de API keys para o OTRS MCP Server.

Fornece endpoints para:
- Login/logout de administradores
- CRUD de API keys para agentes
- Consulta de uso de API keys
- Auditoria de tentativas de login
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from otrs_mcp.auth import (
    create_access_token,
    get_current_admin,
    require_permission,
)
from otrs_mcp.database import (
    create_admin_user,
    create_api_key,
    delete_admin_user,
    delete_api_key,
    get_activity_log,
    get_login_audit,
    list_admin_users,
    list_api_keys,
    record_login_attempt,
    revoke_api_key,
    verify_admin_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ---------------------------------------------------------------------------
# Brute-force protection
# ---------------------------------------------------------------------------

# Configuracao: max tentativas e periodo de lockout
_MAX_LOGIN_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900  # 15 minutos


def _is_locked_out(ip_address: str | None, username: str) -> bool:
    """Verifica lockout consultando tentativas recentes no login_audit (SQLite)."""
    from otrs_mcp.database import get_db

    window_start = (
        datetime.now(timezone.utc) - timedelta(seconds=_LOCKOUT_SECONDS)
    ).isoformat()

    with get_db() as conn:
        # Verificar por username
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM login_audit
               WHERE username = ? AND success = 0 AND created_at >= ?""",
            (username, window_start),
        ).fetchone()
        if row and row["cnt"] >= _MAX_LOGIN_ATTEMPTS:
            return True

        # Verificar por IP
        if ip_address:
            row = conn.execute(
                """SELECT COUNT(*) as cnt FROM login_audit
                   WHERE ip_address = ? AND success = 0 AND created_at >= ?""",
                (ip_address, window_start),
            ).fetchone()
            if row and row["cnt"] >= _MAX_LOGIN_ATTEMPTS:
                return True

    return False


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: int


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6, max_length=128)


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    agent_name: str = Field(min_length=1, max_length=100)
    permissions: list[str] = Field(default=["read"])
    rate_limit: int = Field(default=100, ge=1, le=10000)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class CreateApiKeyResponse(BaseModel):
    id: int
    key: str
    key_prefix: str
    name: str
    agent_name: str
    message: str = "Guarde esta chave. Ela nao sera mostrada novamente."


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request) -> LoginResponse:
    """Autentica um administrador e retorna um token JWT."""
    # Extrair informações para auditoria
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Verificar lockout por IP e por username
    if _is_locked_out(ip_address, body.username):
        logger.warning(
            "Login bloqueado por brute-force protection: user=%s ip=%s",
            body.username,
            ip_address,
        )
        record_login_attempt(
            username=body.username,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente em 15 minutos.",
            headers={"Retry-After": str(_LOCKOUT_SECONDS)},
        )

    user = verify_admin_user(body.username, body.password)
    if user is None:
        # Registrar tentativa falha
        record_login_attempt(
            username=body.username,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas",
        )

    # Registrar tentativa bem-sucedida
    record_login_attempt(
        username=body.username,
        success=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    token = create_access_token(user["id"], user["username"])
    return LoginResponse(
        access_token=token,
        username=user["username"],
        user_id=user["id"],
    )


@router.get("/me")
async def get_me(admin: dict[str, Any] = Depends(get_current_admin)) -> dict[str, Any]:
    """Retorna dados do administrador autenticado."""
    return {"user_id": admin["user_id"], "username": admin["username"]}


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(admin: dict[str, Any] = Depends(get_current_admin)) -> LoginResponse:
    """Renova o JWT do admin autenticado sem exigir senha novamente.

    O token atual deve ser valido (nao expirado). Retorna um novo token
    com novo exp/iat/jti mantendo o mesmo user_id e username.
    """
    new_token = create_access_token(admin["user_id"], admin["username"])
    return LoginResponse(
        access_token=new_token,
        username=admin["username"],
        user_id=admin["user_id"],
    )


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    """Cria um novo administrador."""
    try:
        user = create_admin_user(body.username, body.password)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/users")
async def list_users(
    admin: dict[str, Any] = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    """Lista todos os administradores."""
    return list_admin_users()


@router.delete("/users/{user_id}")
async def remove_user(
    user_id: int,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, str]:
    """Remove um administrador."""
    if admin["user_id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao e possivel remover seu proprio usuario",
        )
    if delete_admin_user(user_id):
        return {"status": "ok", "message": "Usuario removido"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado"
    )


# ---------------------------------------------------------------------------
# API Key Management
# ---------------------------------------------------------------------------


@router.post(
    "/keys", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED
)
async def create_key(
    body: CreateApiKeyRequest,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> CreateApiKeyResponse:
    """Cria uma nova API key para um agente."""
    result = create_api_key(
        name=body.name,
        agent_name=body.agent_name,
        permissions=body.permissions,
        rate_limit=body.rate_limit,
        expires_in_days=body.expires_in_days,
    )
    return CreateApiKeyResponse(**result)


@router.get("/keys")
async def list_keys(
    include_inactive: bool = Query(False),
    admin: dict[str, Any] = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    """Lista todas as API keys."""
    return list_api_keys(include_inactive=include_inactive)


@router.patch("/keys/{key_id}/revoke")
async def revoke_key(
    key_id: int,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, str]:
    """Revoga (desativa) uma API key."""
    if revoke_api_key(key_id):
        return {"status": "ok", "message": "Key revogada"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Key nao encontrada"
    )


@router.delete("/keys/{key_id}")
async def remove_key(
    key_id: int,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, str]:
    """Remove permanentemente uma API key."""
    if delete_api_key(key_id):
        return {"status": "ok", "message": "Key removida"}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Key nao encontrada"
    )


# ---------------------------------------------------------------------------
# Activity / Usage
# ---------------------------------------------------------------------------


@router.get("/activity")
async def list_activity(
    limit: int = Query(50, ge=1, le=500),
    tool: str | None = Query(None),
    status: str | None = Query(None),
    agent: str | None = Query(None),
    admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    """Retorna log de atividade dos agentes."""
    return get_activity_log(
        limit=limit, tool_filter=tool, status_filter=status, agent_filter=agent
    )


@router.get("/login-audit")
async def list_login_audit(
    limit: int = Query(50, ge=1, le=500),
    username: str | None = Query(None),
    success: bool | None = Query(None),
    admin: dict[str, Any] = Depends(get_current_admin),
) -> list[dict[str, Any]]:
    """Retorna log de tentativas de login para auditoria."""
    return get_login_audit(
        limit=limit, username_filter=username, success_filter=success
    )


@router.get("/metrics/daily")
async def daily_metrics(
    days: int = Query(14, ge=1, le=90),
    admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    """Retorna metricas de uso agrupadas por dia para o dashboard."""
    from otrs_mcp.database import get_daily_metrics as _get_daily_metrics

    return _get_daily_metrics(days=days)
