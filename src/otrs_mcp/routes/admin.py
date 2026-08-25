"""Rotas de autenticacao e gerenciamento de API keys para o OTRS MCP Server.

Fornece endpoints para:
- Login/logout de administradores
- CRUD de API keys para agentes
- Consulta de uso de API keys
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    list_admin_users,
    list_api_keys,
    revoke_api_key,
    verify_admin_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
async def login(body: LoginRequest) -> LoginResponse:
    """Autentica um administrador e retorna um token JWT."""
    user = verify_admin_user(body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas",
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
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")


# ---------------------------------------------------------------------------
# API Key Management
# ---------------------------------------------------------------------------


@router.post("/keys", response_model=CreateApiKeyResponse, status_code=status.HTTP_201_CREATED)
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
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key nao encontrada")


@router.delete("/keys/{key_id}")
async def remove_key(
    key_id: int,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, str]:
    """Remove permanentemente uma API key."""
    if delete_api_key(key_id):
        return {"status": "ok", "message": "Key removida"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key nao encontrada")


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
    return get_activity_log(limit=limit, tool_filter=tool, status_filter=status, agent_filter=agent)
