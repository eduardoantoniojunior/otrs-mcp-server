# OTRS MCP Server - Guia do Projeto

## Visao Geral

Servidor MCP (Model Context Protocol) para integracao com o OTRS (sistema de tickets). Permite que LLMs criem, consultem, busquem e atualizem tickets no OTRS.

## Estrutura do Projeto

```
otrs-mcp-server/
├── src/otrs_mcp/
│   ├── __init__.py      # Public API
│   ├── main.py          # Entry point (MCP server)
│   ├── config.py        # Configuracao (Pydantic BaseSettings)
│   ├── client.py        # Cliente HTTP com retry
│   ├── tools.py         # Tools MCP
│   ├── resources.py     # Resources MCP
│   ├── api.py           # Backend REST (FastAPI)
│   ├── exceptions.py    # Excecoes customizadas
│   └── constants.py     # Constantes
├── frontend/            # Frontend React + TypeScript
├── tests/
│   ├── unit/            # Testes unitarios
│   └── integration/     # Testes de integracao
├── Dockerfile           # MCP server container
├── Dockerfile.api       # API container
├── docker-compose.yml   # Orquestracao
└── pyproject.toml       # Config do projeto (uv/hatch)
```

## Comandos Uteis

```bash
# Instalar dependencias
uv sync
uv sync --extra dev

# Rodar o MCP server
uv run python -m otrs_mcp.main

# Rodar a API REST
uv run uvicorn otrs_mcp.api:app --port 3000

# Rodar testes
uv run pytest tests/unit/ -v

# Rodar testes com cobertura
uv run pytest tests/unit/ --cov=src/otrs_mcp --cov-report=term-missing

# Formatacao
uv run black src/
uv run isort src/

# Type check
uv run mypy src/

# Docker
docker compose up -d
docker compose logs -f
docker compose down
```

## Variaveis de Ambiente

| Variavel | Obrigatoria | Descricao |
|---|---|---|
| `OTRS_BASE_URL` | Sim | URL base do OTRS |
| `OTRS_USERNAME` | Sim | Usuario do OTRS |
| `OTRS_PASSWORD` | Sim | Senha do OTRS |
| `OTRS_VERIFY_SSL` | Nao | Verificar SSL (default: false) |
| `OTRS_TIMEOUT` | Nao | Timeout HTTP em segundos (default: 30) |
| `OTRS_DEFAULT_QUEUE` | Nao | Fila padrao (default: Raw) |
| `OTRS_DEFAULT_STATE` | Nao | Estado padrao (default: new) |
| `OTRS_DEFAULT_PRIORITY` | Nao | Prioridade padrao (default: 3 normal) |

## Convencoes de Codigo

- Python 3.12+
- Type hints obrigatorios
- Formatacao com black (88 chars)
- Imports ordenados com isort
- Testes com pytest + pytest-asyncio

## Funcionalidades Implementadas

### Tools MCP
- `create_ticket` - Criar ticket
- `get_ticket` - Obter detalhes do ticket
- `search_tickets` - Buscar tickets
- `update_ticket` - Atualizar ticket
- `get_ticket_history` - Historico do ticket

### Resources MCP
- `otrs://ticket/{ticket_id}` - Dados do ticket
- `otrs://ticket/{ticket_id}/history` - Historico
- `otrs://search/tickets` - Tickets recentes

### API REST (FastAPI)
- `GET /api/health` - Health check
- `GET /api/tickets` - Listar tickets
- `GET /api/tickets/{id}` - Detalhes do ticket
- `POST /api/tickets` - Criar ticket
- `PUT /api/tickets/{id}` - Atualizar ticket
- `GET /api/tickets/{id}/history` - Historico do ticket

### Frontend (React)
- Dashboard com metricas
- Lista de tickets com busca e filtros
- Criacao e edicao de tickets
- Visualizacao de detalhes e historico
