"""Backend REST API para o OTRS MCP Server."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from otrs_mcp.client import OTRSClient
from otrs_mcp.config import OTRSConfig

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
    except Exception as e:
        logger.error("Erro ao buscar tickets: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: str) -> dict:
    client = _get_client()
    try:
        return await client.get_ticket(ticket_id=ticket_id)
    except Exception as e:
        logger.error("Erro ao obter ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tickets", status_code=201)
async def create_ticket(ticket: TicketCreate) -> dict:
    client = _get_client()
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
    except Exception as e:
        logger.error("Erro ao criar ticket: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, ticket: TicketUpdate) -> dict:
    client = _get_client()
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
    except Exception as e:
        logger.error("Erro ao atualizar ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tickets/{ticket_id}/history")
async def get_ticket_history(ticket_id: str) -> dict:
    client = _get_client()
    try:
        return await client.get_ticket_history(ticket_id=ticket_id)
    except Exception as e:
        logger.error("Erro ao obter historico do ticket %s: %s", ticket_id, e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000)
