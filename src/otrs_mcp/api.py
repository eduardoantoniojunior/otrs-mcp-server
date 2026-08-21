"""Backend REST API para o OTRS MCP Server."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig
from otrs_mcp.constants import VALID_PRIORITIES
from otrs_mcp.activity import get_activity, get_summary, clear_activity
from otrs_mcp.exceptions import (
    OTRSAPIError,
    OTRSAuthenticationError,
    OTRSConnectionError,
    OTRSTicketNotFoundError,
    OTRSValidationError,
)

logger = logging.getLogger(__name__)

_client: OTRSClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    config = OTRSConfig()
    global _client
    _client = OTRSClient(config)
    logger.info("API iniciada com conexao ao OTRS: %s", config.base_url)
    yield
    logger.info("API encerrada")


app = FastAPI(
    title="OTRS MCP API",
    description="REST API para gerenciamento de tickets OTRS",
    version="0.1.0",
    lifespan=lifespan,
)

cors_origins = os.getenv("OTRS_CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


def _get_client() -> OTRSClient:
    if _client is None:
        raise HTTPException(status_code=503, detail="API nao inicializada")
    return _client


class TicketCreate(BaseModel):
    title: str
    body: str
    queue: str | None = None
    priority: str | None = None
    state: str | None = None
    customer_user: str | None = None
    ticket_type: str | None = None


class TicketUpdate(BaseModel):
    title: str | None = None
    queue: str | None = None
    priority: str | None = None
    state: str | None = None
    customer_user: str | None = None
    owner: str | None = None


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/tickets")
async def list_tickets(
    customer_user: str | None = Query(None),
    queue: str | None = Query(None),
    state: str | None = Query(None),
    priority: str | None = Query(None),
    title: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("Age"),
    order_by: str = Query("Down"),
) -> dict:
    client = _get_client()
    try:
        return await client.search_tickets(
            customer_user=customer_user,
            queue=queue,
            state=state,
            priority=priority,
            title=title,
            limit=limit,
            sort_by=sort_by,
            order_by=order_by,
        )
    except OTRSConnectionError as e:
        logger.error("Erro de conexao ao buscar tickets: %s", e)
        raise HTTPException(status_code=503, detail="Servico OTRS indisponivel")
    except OTRSAuthenticationError as e:
        logger.error("Erro de autenticacao ao buscar tickets: %s", e)
        raise HTTPException(status_code=401, detail="Credenciais OTRS invalidas")
    except OTRSAPIError as e:
        logger.error("Erro da API OTRS ao buscar tickets: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro na API OTRS: {str(e)}")
    except Exception as e:
        logger.error("Erro inesperado ao buscar tickets: %s", e)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: str) -> dict:
    client = _get_client()
    try:
        return await client.get_ticket(ticket_id=ticket_id)
    except OTRSTicketNotFoundError as e:
        logger.error("Ticket %s nao encontrado: %s", ticket_id, e)
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} nao encontrado")
    except OTRSConnectionError as e:
        logger.error("Erro de conexao ao obter ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=503, detail="Servico OTRS indisponivel")
    except OTRSAuthenticationError as e:
        logger.error("Erro de autenticacao ao obter ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=401, detail="Credenciais OTRS invalidas")
    except OTRSAPIError as e:
        logger.error("Erro da API OTRS ao obter ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=502, detail=f"Erro na API OTRS: {str(e)}")
    except Exception as e:
        logger.error("Erro inesperado ao obter ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.post("/api/tickets", status_code=201)
async def create_ticket(ticket: TicketCreate) -> dict:
    client = _get_client()
    if ticket.priority and ticket.priority.lower() not in {p.lower() for p in VALID_PRIORITIES}:
        raise HTTPException(
            status_code=422,
            detail=f"Prioridade invalida: '{ticket.priority}'. Valores validos: {', '.join(sorted(VALID_PRIORITIES))}",
        )
    try:
        return await client.create_ticket(
            title=ticket.title,
            body=ticket.body,
            queue=ticket.queue,
            priority=ticket.priority,
            state=ticket.state,
            customer_user=ticket.customer_user,
            ticket_type=ticket.ticket_type,
        )
    except OTRSConnectionError as e:
        logger.error("Erro de conexao ao criar ticket: %s", e)
        raise HTTPException(status_code=503, detail="Servico OTRS indisponivel")
    except OTRSAuthenticationError as e:
        logger.error("Erro de autenticacao ao criar ticket: %s", e)
        raise HTTPException(status_code=401, detail="Credenciais OTRS invalidas")
    except OTRSAPIError as e:
        logger.error("Erro da API OTRS ao criar ticket: %s", e)
        raise HTTPException(status_code=502, detail=f"Erro na API OTRS: {str(e)}")
    except Exception as e:
        logger.error("Erro inesperado ao criar ticket: %s", e)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.put("/api/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, ticket: TicketUpdate) -> dict:
    client = _get_client()
    if ticket.priority and ticket.priority.lower() not in {p.lower() for p in VALID_PRIORITIES}:
        raise HTTPException(
            status_code=422,
            detail=f"Prioridade invalida: '{ticket.priority}'. Valores validos: {', '.join(sorted(VALID_PRIORITIES))}",
        )
    try:
        return await client.update_ticket(
            ticket_id=ticket_id,
            title=ticket.title,
            queue=ticket.queue,
            priority=ticket.priority,
            state=ticket.state,
            customer_user=ticket.customer_user,
            owner=ticket.owner,
        )
    except OTRSTicketNotFoundError as e:
        logger.error("Ticket %s nao encontrado ao atualizar: %s", ticket_id, e)
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} nao encontrado")
    except OTRSConnectionError as e:
        logger.error("Erro de conexao ao atualizar ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=503, detail="Servico OTRS indisponivel")
    except OTRSAuthenticationError as e:
        logger.error("Erro de autenticacao ao atualizar ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=401, detail="Credenciais OTRS invalidas")
    except OTRSAPIError as e:
        logger.error("Erro da API OTRS ao atualizar ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=502, detail=f"Erro na API OTRS: {str(e)}")
    except Exception as e:
        logger.error("Erro inesperado ao atualizar ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.get("/api/tickets/{ticket_id}/history")
async def get_ticket_history(ticket_id: str) -> dict:
    client = _get_client()
    try:
        return await client.get_ticket_history(ticket_id=ticket_id)
    except OTRSTicketNotFoundError as e:
        logger.error("Ticket %s nao encontrado ao buscar historico: %s", ticket_id, e)
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} nao encontrado")
    except OTRSConnectionError as e:
        logger.error("Erro de conexao ao obter historico do ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=503, detail="Servico OTRS indisponivel")
    except OTRSAuthenticationError as e:
        logger.error("Erro de autenticacao ao obter historico do ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=401, detail="Credenciais OTRS invalidas")
    except OTRSAPIError as e:
        logger.error("Erro da API OTRS ao obter historico do ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=502, detail=f"Erro na API OTRS: {str(e)}")
    except Exception as e:
        logger.error("Erro inesperado ao obter historico do ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@app.get("/api/activity")
async def list_activity(
    limit: int = Query(50, ge=1, le=500),
    tool: str | None = Query(None),
    status: str | None = Query(None),
) -> dict:
    return get_activity(limit=limit, tool_filter=tool, status_filter=status)


@app.get("/api/activity/summary")
async def activity_summary() -> dict:
    return get_summary()


@app.delete("/api/activity")
async def reset_activity() -> dict[str, str]:
    clear_activity()
    return {"status": "ok", "message": "Atividade limpa com sucesso"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000)
