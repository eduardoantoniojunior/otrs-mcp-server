# OTRS MCP Server - Guia do Projeto

## Visao Geral

Servidor MCP (Model Context Protocol) para integracao com o OTRS (sistema de tickets). Permite que LLMs criem, consultem, busquem e atualizem tickets no OTRS. Inclui API REST autenticada (JWT + API Keys), painel administrativo React e deploy via Docker + Nginx.

## Estrutura do Projeto

```
otrs-mcp-server/
├── src/otrs_mcp/
│   ├── __init__.py      # Public API
│   ├── main.py          # Entry point (MCP server stdio/http)
│   ├── config.py        # Configuracao (Pydantic BaseSettings)
│   ├── client.py        # Cliente HTTP OTRS com retry
│   ├── tools.py         # Tools MCP (5 tools)
│   ├── resources.py     # Resources MCP (3 resources)
│   ├── api.py           # Backend REST (FastAPI)
│   ├── auth.py          # JWT + API key + rate limiting
│   ├── database.py      # SQLite WAL (schema + CRUD)
│   ├── activity.py      # Monitoramento de atividade
│   ├── exceptions.py    # Excecoes customizadas
│   ├── constants.py     # Constantes
│   └── routes/
│       └── admin.py     # Rotas admin (login, keys, users, audit)
├── frontend/            # Frontend React + TypeScript + TailwindCSS
│   ├── src/             # Paginas, componentes, hooks, services
│   ├── Dockerfile       # Build Node + serve Nginx Alpine
│   └── nginx.conf       # Config Nginx do container frontend
├── nginx/
│   └── mcp.conf          # Config Nginx do servidor host (HTTPS)
├── tests/
│   ├── unit/            # Testes unitarios
│   └── integration/     # Testes de integracao
├── Dockerfile           # MCP server container
├── Dockerfile.api       # API container
├── docker-compose.yml   # 3 servicos (api, mcp-server, frontend)
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
docker compose up -d --build
docker compose logs -f
docker compose down
```

## Variaveis de Ambiente

| Variavel | Obrigatoria | Descricao |
|---|---|---|
| `OTRS_BASE_URL` | Sim | URL base do webservice OTRS |
| `OTRS_USERNAME` | Sim | Usuario do OTRS |
| `OTRS_PASSWORD` | Sim | Senha do OTRS |
| `OTRS_VERIFY_SSL` | Nao | Verificar SSL (default: true) |
| `OTRS_TIMEOUT` | Nao | Timeout HTTP em segundos (default: 30) |
| `OTRS_DEFAULT_QUEUE` | Nao | Fila padrao (default: Raw) |
| `OTRS_DEFAULT_STATE` | Nao | Estado padrao (default: new) |
| `OTRS_DEFAULT_PRIORITY` | Nao | Prioridade padrao (default: 3 normal) |
| `OTRS_JWT_SECRET` | Producao | Secret JWT (obrigatorio em production) |
| `OTRS_ADMIN_PASSWORD` | Sim | Senha do admin padrao |
| `OTRS_MCP_TRANSPORT` | Nao | Transporte: stdio ou http (default: stdio) |
| `OTRS_DB_PATH` | Nao | Caminho do SQLite (default: /data/otrs-mcp.db) |

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
- `GET /api/config` - Configuracao (filas, tipos)
- `GET /api/tickets` - Listar tickets
- `GET /api/tickets/{id}` - Detalhes do ticket
- `POST /api/tickets` - Criar ticket
- `PUT /api/tickets/{id}` - Atualizar ticket
- `GET /api/tickets/{id}/history` - Historico do ticket
- `GET /api/activity` - Log de atividade
- `GET /api/activity/summary` - Resumo de metricas
- `POST /api/admin/login` - Login admin
- `POST /api/admin/keys` - Criar API key
- `GET /api/admin/keys` - Listar API keys
- `GET /api/admin/activity` - Atividade detalhada
- `GET /api/admin/login-audit` - Log de tentativas de login

### Frontend (React)
- Dashboard com metricas e alertas de seguranca
- MCP Tokens (CRUD, filtros, rate limit, indicadores)
- Admin Users (gerenciamento)
- Audit Log (filtros + export CSV/JSON)
- Login Audit (tentativas de login + export)
- Client MCP Wizard (configuracoes para clientes)
- Settings (status conexao OTRS)

### Deploy
- Docker Compose com 3 servicos (api, mcp-server, frontend)
- Nginx como reverse proxy HTTPS (Certbot/Let's Encrypt)
- Portas expostas apenas em 127.0.0.1 (seguranca)
- Volume compartilhado para SQLite e atividade
