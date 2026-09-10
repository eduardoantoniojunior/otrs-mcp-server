# OTRS MCP Server

Servidor [Model Context Protocol][mcp] (MCP) para integração com o [OTRS](https://otrs.org/) (Open Ticket Request System).

Permite que assistentes de IA (Claude Desktop, VS Code, Kiro, agentes Python) criem, consultem, busquem e atualizem tickets no OTRS por uma interface padronizada. Acompanha uma API REST autenticada, painel administrativo em React, auditoria em SQLite e instrumentação OpenTelemetry.

[mcp]: https://modelcontextprotocol.io/introduction

**Versão:** 0.2.0 · **Python:** 3.12+ · **Licença:** Apache-2.0

---

## Sumário

- [O que o servidor oferece](#o-que-o-servidor-oferece)
- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [Início rápido](#início-rápido)
- [Como usar o MCP](#como-usar-o-mcp)
- [Tools MCP](#tools-mcp)
- [Resources MCP](#resources-mcp)
- [API REST](#api-rest)
- [Configuração](#configuração)
- [API keys](#api-keys)
- [Painel administrativo](#painel-administrativo)
- [Segurança](#segurança)
- [Observabilidade](#observabilidade)
- [Deploy em produção](#deploy-em-produção)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Desenvolvimento](#desenvolvimento)
- [Limitações conhecidas](#limitações-conhecidas)
- [Solução de problemas](#solução-de-problemas)

---

## O que o servidor oferece

Três formas de consumir o mesmo backend OTRS:

| Interface | Para quem | Autenticação |
|---|---|---|
| **MCP** (`streamable-http`) | Agentes de IA e clientes MCP remotos | API key obrigatória no header `Authorization` |
| **MCP** (`stdio`) | Cliente MCP local que sobe o processo | Nenhuma (sem rede; credenciais vêm do ambiente) |
| **API REST** (FastAPI) | Scripts, integrações, o próprio frontend | API key ou JWT |
| **Painel web** (React) | Administradores humanos | JWT (login com usuário e senha) |

Operações OTRS cobertas: `SessionCreate`, `TicketCreate`, `TicketGet`, `TicketSearch`, `TicketUpdate`, `TicketHistoryGet`.

---

## Arquitetura

```
┌────────────────────────┐      ┌────────────────────────┐
│  Agente IA / cliente   │      │  Navegador (admin)     │
│  MCP                   │      │                        │
└───────────┬────────────┘      └───────────┬────────────┘
            │ Bearer sk-otrs-...            │ Bearer JWT
            ▼                               ▼
┌──────────────────────────────────────────────────────────┐
│        Nginx no host (nginx/mcp.conf) + Certbot          │
│  /otrs/mcp → 8001   /otrs/api/ → 3000   /otrs/ → SPA     │
└──────┬──────────────────┬──────────────────┬─────────────┘
       ▼                  ▼                  ▼
┌────────────┐     ┌────────────┐     ┌────────────┐
│ mcp-server │     │    api     │     │  frontend  │
│  FastMCP   │     │  FastAPI   │     │ React+Nginx│
│ :8001      │     │ :3000      │     │ :80        │
└─────┬──────┘     └─────┬──────┘     └────────────┘
      │                  │
      │                  ▼
      │        ┌──────────────────────┐
      │        │ SQLite (WAL)         │
      │        │ /data/otrs-mcp.db    │
      │        │ admin_users,api_keys,│
      │        │ api_usage,login_audit│
      │        └──────────────────────┘
      ▼                  ▼
┌──────────────────────────────────┐   ┌─────────────────────┐
│   Servidor OTRS                  │   │  otel-collector     │
│   (Generic Interface)            │   │  → Tempo / Mimir    │
└──────────────────────────────────┘   └─────────────────────┘
```

### Serviços do Docker Compose

| Serviço | Imagem / build | Porta publicada | Limites |
|---|---|---|---|
| `api` | `Dockerfile.api` (python:3.12.8-slim) | `127.0.0.1:3000` | 1 CPU / 512M |
| `mcp-server` | `Dockerfile` (python:3.12.8-slim) | `127.0.0.1:8001` | 1 CPU / 512M |
| `frontend` | `frontend/Dockerfile` (build Vite + Nginx) | `127.0.0.1:8081` | 0.5 CPU / 128M |
| `otel-collector` | `otel/opentelemetry-collector-contrib:0.108.0` | `127.0.0.1:4317` e `:4318` | 0.5 CPU / 256M |

Todas as portas ficam em `127.0.0.1`. A exposição pública é feita pelo Nginx do host.

---

## Pré-requisitos

- Docker e Docker Compose
- Servidor OTRS com **Generic Interface** habilitada
- Para produção: Nginx e Certbot no host, domínio apontando para o servidor

### Configurar o webservice no OTRS

1. Vá em **Administração → Web Services**
2. Crie ou edite um webservice expondo: `SessionCreate`, `TicketCreate`, `TicketGet`, `TicketSearch`, `TicketUpdate`, `TicketHistoryGet`
3. Anote a URL: `https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/NomeDoWebservice`
4. Garanta que o usuário configurado tem permissão nas filas usadas

---

## Início rápido

```bash
git clone https://github.com/eduardoantoniojunior/otrs-mcp-server.git
cd otrs-mcp-server
cp .env.example .env
```

Preencha o mínimo no `.env`:

```env
OTRS_BASE_URL=https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/MCPConnector
OTRS_USERNAME=seu-usuario
OTRS_PASSWORD=sua-senha

OTRS_ADMIN_USER=admin
OTRS_ADMIN_PASSWORD=escolha-uma-senha-forte
OTRS_JWT_SECRET=<saída de: python -c "import secrets; print(secrets.token_hex(32))">
```

Suba os containers:

```bash
docker compose up -d --build
docker compose ps
curl -s http://127.0.0.1:3000/api/health   # {"status":"ok"}
```

O usuário admin é criado no primeiro start, somente se ainda não existir nenhum e `OTRS_ADMIN_PASSWORD` estiver definido. Acesse o painel em `http://127.0.0.1:8081` (ou pela URL pública do Nginx), faça login e crie sua primeira API key.

### Rodar sem Docker

```bash
uv sync --extra dev

# API REST em :3000
uv run uvicorn otrs_mcp.api:app --port 3000 --reload

# MCP em HTTP na :8001
$env:OTRS_MCP_TRANSPORT="http"; uv run python -m otrs_mcp.main

# Frontend em :5173
cd frontend; npm ci; npm run dev
```

---

## Como usar o MCP

O servidor fala dois transportes, definidos por `OTRS_MCP_TRANSPORT`:

- `stdio` (padrão) — o cliente sobe o processo local e conversa por pipe. Não precisa de rede nem de API key.
- `http` — Streamable HTTP em `/mcp`, para agentes remotos. **Exige API key válida em toda requisição.**

### Autenticação no transporte HTTP

Requisições sem `Authorization: Bearer sk-otrs-...` são recusadas com `401` antes de qualquer tool executar:

```json
{"error": "invalid_token", "error_description": "Authentication required"}
```

São recusadas as keys inexistentes, revogadas (`active = 0`) e vencidas (`expires_at` no passado). A validação usa a mesma tabela `api_keys` da API REST, e as permissões da key viram escopos:

| Permissão da key | Tools liberadas |
|---|---|
| `read` | `get_ticket`, `search_tickets`, `get_ticket_history` e os resources |
| `write` | `create_ticket`, `update_ticket` |
| `admin` | todas |

Uma key só de leitura que tente escrever recebe erro na tool, não na conexão:

```
Permissao 'write' necessaria. A API key possui: read
```

### Claude Desktop / Kiro — remoto (HTTP)

```json
{
  "mcpServers": {
    "otrs": {
      "url": "https://seu-dominio/otrs/mcp",
      "headers": {
        "Authorization": "Bearer sk-otrs-sua-api-key"
      }
    }
  }
}
```

O path `/otrs/mcp` corresponde ao `nginx/mcp.conf` deste repositório. Em domínio dedicado, use `https://seu-dominio/mcp`.

### VS Code

```json
{
  "servers": {
    "otrs": {
      "type": "http",
      "url": "https://seu-dominio/otrs/mcp",
      "headers": {
        "Authorization": "Bearer sk-otrs-sua-api-key"
      }
    }
  }
}
```

### Local via stdio

```json
{
  "mcpServers": {
    "otrs": {
      "command": "uv",
      "args": ["run", "python", "-m", "otrs_mcp.main"],
      "cwd": "/caminho/para/otrs-mcp-server",
      "env": {
        "OTRS_BASE_URL": "https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/MCPConnector",
        "OTRS_USERNAME": "usuario",
        "OTRS_PASSWORD": "senha",
        "OTRS_MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### Python SDK

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main() -> None:
    headers = {"Authorization": "Bearer sk-otrs-sua-api-key"}
    async with streamablehttp_client(
        "https://seu-dominio/otrs/mcp", headers=headers
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print([t.name for t in tools.tools])

            result = await session.call_tool(
                "search_tickets",
                arguments={"state": "new", "limit": 5},
            )
            print(result)


asyncio.run(main())
```

### Exemplos de pedidos ao agente

Com o MCP conectado, o modelo resolve pedidos em linguagem natural:

- "Abra um ticket na fila Suporte com prioridade 4 high sobre a impressora do 3º andar"
- "Quais tickets estão em aberto na fila Infraestrutura?"
- "Mostre o histórico do ticket 4821"
- "Mude o ticket 4821 para closed successful"

Toda resposta de ticket inclui `WebURL` (e `HistoryWebURL`, quando aplicável) apontando para a interface web do OTRS, o que dá ao agente um link clicável para devolver ao usuário.

---

## Tools MCP

| Tool | Parâmetros | Observações |
|---|---|---|
| `create_ticket` | `title`, `body`, `queue?`, `priority?`, `state?`, `customer_user?`, `ticket_type?` | Aplica os defaults de `OTRS_DEFAULT_*`; valida prioridade |
| `get_ticket` | `ticket_id`, `include_dynamic_fields?`, `include_extended_data?` | `ticket_id` precisa ser numérico |
| `search_tickets` | `customer_user?`, `customer_id?`, `queue?`, `state?`, `priority?`, `title?`, `limit?`, `sort_by?`, `order_by?` | `title` aceita `*` como curinga (convertido para `%`) |
| `update_ticket` | `ticket_id`, `title?`, `queue?`, `priority?`, `state?`, `customer_user?`, `owner?` | Envia só os campos preenchidos |
| `get_ticket_history` | `ticket_id` | — |

Prioridades aceitas (`src/otrs_mcp/constants.py`): `1 very low`, `2 low`, `3 normal`, `4 high`, `5 very high`.

Cada chamada é registrada em `activity.json` com tool, status, duração e `ticket_id`. Campos chamados `password` são removidos antes de gravar.

---

## Resources MCP

| URI | Conteúdo |
|---|---|
| `otrs://ticket/{ticket_id}` | Ticket completo em JSON |
| `otrs://ticket/{ticket_id}/history` | Histórico do ticket |
| `otrs://search/tickets` | Os 20 tickets mais recentes |

---

## API REST

Base: `https://seu-dominio/otrs/api` (ou `http://127.0.0.1:3000/api` local).

Autenticação por header, exceto no health check:

```
Authorization: Bearer <api-key-ou-jwt>
```

### Público

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/health` | Health check |

### Tickets — API key ou JWT

| Método | Rota | Permissão |
|---|---|---|
| `GET` | `/api/tickets` | `read` |
| `GET` | `/api/tickets/{id}` | `read` |
| `POST` | `/api/tickets` | `write` |
| `PUT` | `/api/tickets/{id}` | `write` |
| `GET` | `/api/tickets/{id}/history` | `read` |
| `GET` | `/api/config` | autenticado |

Filtros de `GET /api/tickets`: `customer_user`, `customer_id`, `queue`, `state`, `priority`, `title`, `limit` (1–200), `sort_by`, `order_by`.

### Atividade — API key ou JWT

| Método | Rota | Permissão |
|---|---|---|
| `GET` | `/api/activity` | autenticado |
| `GET` | `/api/activity/summary` | autenticado |
| `DELETE` | `/api/activity` | `write` |

### Administração — somente JWT

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/admin/login` | Login, devolve JWT |
| `POST` | `/api/admin/refresh` | Renova o JWT sem pedir senha |
| `GET` | `/api/admin/me` | Admin autenticado |
| `POST` `GET` `DELETE` | `/api/admin/users[/{id}]` | CRUD de administradores |
| `POST` `GET` | `/api/admin/keys` | Criar e listar API keys |
| `PATCH` | `/api/admin/keys/{id}/revoke` | Desativar key |
| `DELETE` | `/api/admin/keys/{id}` | Remover key |
| `GET` | `/api/admin/activity` | Auditoria de uso (SQLite) |
| `GET` | `/api/admin/login-audit` | Tentativas de login |
| `GET` | `/api/admin/metrics/daily` | Métricas por dia (`days`, 1–90) |

### Exemplo com cURL

```bash
KEY="sk-otrs-sua-api-key"
BASE="https://seu-dominio/otrs/api"

# Buscar tickets novos
curl -s -H "Authorization: Bearer $KEY" "$BASE/tickets?state=new&limit=5"

# Criar ticket
curl -s -X POST "$BASE/tickets" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Impressora sem toner","body":"3o andar, sala 12","queue":"Suporte","priority":"3 normal"}'

# Fechar ticket
curl -s -X PUT "$BASE/tickets/4821" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"state":"closed successful"}'
```

### Códigos de erro

| Código | Significado |
|---|---|
| `401` | Token ausente, inválido, expirado ou key revogada |
| `403` | Permissão insuficiente para a operação |
| `404` | Ticket não encontrado |
| `422` | Validação falhou (`ticket_id` não numérico, prioridade inválida) |
| `429` | Rate limit da API key, ou lockout de login |
| `502` | Erro na comunicação com o OTRS |
| `503` | OTRS indisponível ou API ainda inicializando |

---

## Configuração

Todas as variáveis usam o prefixo `OTRS_` e são lidas do ambiente (`pydantic-settings`).

### OTRS — obrigatórias

| Variável | Descrição |
|---|---|
| `OTRS_BASE_URL` | URL completa do webservice |
| `OTRS_USERNAME` | Usuário do OTRS |
| `OTRS_PASSWORD` | Senha do OTRS |

Faltando qualquer uma, o processo falha no start com `OTRSValidationError`.

### OTRS — opcionais

| Variável | Padrão | Descrição |
|---|---|---|
| `OTRS_VERIFY_SSL` | `true` | Verificação de certificado |
| `OTRS_TIMEOUT` | `30` | Timeout HTTP (s) |
| `OTRS_DEBUG` | `false` | Log de debug por requisição |
| `OTRS_DEFAULT_QUEUE` | `Raw` | Fila padrão |
| `OTRS_DEFAULT_STATE` | `new` | Estado padrão |
| `OTRS_DEFAULT_PRIORITY` | `3 normal` | Prioridade padrão |
| `OTRS_DEFAULT_TYPE` | vazio | Tipo padrão (omitido se vazio) |
| `OTRS_WEB_BASE_URL` | derivado | Base da interface web, usada nos links `WebURL` |
| `OTRS_VALID_QUEUES` | vazio | Filas do dropdown do painel (separadas por vírgula) |
| `OTRS_VALID_TYPES` | vazio | Tipos do dropdown do painel |

Quando `OTRS_WEB_BASE_URL` não é informado, ele é derivado de `OTRS_BASE_URL` cortando em `/nph-genericinterface.pl`.

### Autenticação

| Variável | Padrão | Descrição |
|---|---|---|
| `OTRS_ENV` | `development` | Com `production`, `OTRS_JWT_SECRET` passa a ser obrigatório |
| `OTRS_JWT_SECRET` | gerado | Segredo HS256. Sem ele em dev, um aleatório é gerado e os tokens morrem a cada restart |
| `OTRS_JWT_EXPIRE_MINUTES` | `480` | Validade do JWT |
| `OTRS_ADMIN_USER` | `admin` | Admin criado no primeiro start |
| `OTRS_ADMIN_PASSWORD` | — | Sem isso, nenhum admin é criado automaticamente |

### MCP, banco e CORS

| Variável | Padrão | Descrição |
|---|---|---|
| `OTRS_MCP_TRANSPORT` | `stdio` | `stdio` ou `http`. Com `http`, a API key passa a ser exigida |
| `OTRS_MCP_HOST` | `0.0.0.0` | Bind do MCP em modo http |
| `OTRS_MCP_PORT` | `8001` | Porta do MCP em modo http |
| `OTRS_MCP_ISSUER_URL` | `https://otrs-mcp.local` | Valor de `issuer_url` exigido pelas AuthSettings do SDK; não há OAuth externo |
| `OTRS_DB_PATH` | `/data/otrs-mcp.db` | Caminho do SQLite |
| `OTRS_ACTIVITY_FILE` | `/data/activity.json` | Log de atividade do MCP |
| `OTRS_ACTIVITY_MAX_EVENTS` | `1000` | Eventos mantidos no JSON |
| `OTRS_CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` | Origens permitidas |

### Frontend e telemetria

| Variável | Padrão | Descrição |
|---|---|---|
| `VITE_BASE_PATH` | `/` | Subpath do build (ex.: `/otrs/`). Aplicado em build time |
| `VITE_OTEL_ENDPOINT` | vazio | Collector para traces do browser |
| `OTEL_TEMPO_ENDPOINT` | vazio | Destino OTLP do collector |

---

## API keys

Formato: `sk-otrs-` seguido de 64 caracteres hex. A chave é exibida **uma única vez**, na criação; o banco guarda apenas o SHA-256 e um prefixo de 12 caracteres para identificação.

Criar pelo painel: **MCP Tokens → Create Token**. Ou via API:

```bash
curl -s -X POST "$BASE/admin/keys" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"Agente Suporte","agent_name":"suporte-bot","permissions":["read","write"],"rate_limit":100,"expires_in_days":90}'
```

| Campo | Regra |
|---|---|
| `permissions` | `read`, `write`, `admin`. `admin` satisfaz qualquer verificação |
| `rate_limit` | Requisições por minuto, 1–10000 |
| `expires_in_days` | 1–365, ou omitido para não expirar |

Uma key é rejeitada se não existir, estiver revogada (`active = 0`) ou vencida.

---

## Painel administrativo

React 19 + Vite 6 + TanStack Query 5 + Tailwind.

| Página | Função |
|---|---|
| **Dashboard** | Métricas de uso, atividade por dia, distribuição por tool, ranking de agentes |
| **MCP Tokens** | Criar, revogar e remover API keys; permissões, rate limit, expiração |
| **Admin Users** | Gerenciar administradores |
| **Audit Log** | Operações registradas em `api_usage`, com agente, key, ticket e duração |
| **Login Audit** | Tentativas de login com IP e user agent |
| **Client MCP Wizard** | Gera a configuração pronta para Claude Desktop, VS Code, Python e cURL |
| **Settings** | Estado da conexão com o OTRS, filas e tipos configurados |

Também há componentes de ticket (`TicketList`, `TicketDetail`, `TicketForm`) para operar tickets pelo painel.

---

## Segurança

| Camada | Implementação |
|---|---|
| **Rede** | Portas dos containers em `127.0.0.1`; exposição via Nginx com TLS (Certbot) |
| **Senhas** | bcrypt via `passlib` para admins |
| **API keys** | SHA-256 no banco, valor bruto nunca persistido |
| **MCP HTTP** | `TokenVerifier` valida a API key em cada requisição; `RequireAuthMiddleware` responde `401` antes de executar tool. Escopo `read`/`write` verificado por tool |
| **JWT** | HS256 com `sub`, `username`, `exp`, `iat`, `jti`, `type` |
| **Produção** | `OTRS_ENV=production` sem `OTRS_JWT_SECRET` aborta o start |
| **Brute-force** | 5 falhas em 15 min por usuário **ou** por IP → `429`, avaliado sobre `login_audit` |
| **Rate limit** | Janela de 60 s por API key sobre `api_usage`; `rate_limit` 0 libera |
| **Permissões** | `require_permission("read"/"write")` em cada rota de ticket |
| **Headers** | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, `Cache-Control: no-store`; Nginx adiciona `Permissions-Policy` |
| **CORS** | Origens por `OTRS_CORS_ORIGINS`, `allow_headers` restrito a `Authorization` e `Content-Type` |
| **Validação** | `ticket_id` por regex `^\d{1,20}$`, prioridade contra lista fechada, Pydantic com `min_length`/`max_length` |
| **Sanitização** | Erros do OTRS viram `502 "Erro na comunicacao com o OTRS"`; detalhes só no log |
| **Sessão OTRS** | `SessionCreate` protegido por `asyncio.Lock`; requisições seguintes enviam apenas `SessionID` |
| **Auditoria** | Toda operação de ticket grava agente, key, ticket e duração em `api_usage` |
| **Containers** | Usuário não-root `otrs`, multi-stage, imagens pinadas (`python:3.12.8`, `uv:0.5`), limites de CPU e memória |
| **Fail2ban** | Jails em `deploy/fail2ban/` para login, abuso de API e varredura de bots |

Segredos ficam apenas em variáveis de ambiente. `record_activity` e `record_tool_call` descartam campos `password` antes de gravar.

---

## Observabilidade

Backend instrumentado sem alteração de código: os Dockerfiles usam `opentelemetry-instrument` como wrapper, com instrumentações de FastAPI, httpx, SQLite3 e logging.

```
api / mcp-server ──gRPC:4317──▶ otel-collector ──OTLP HTTP──▶ Tempo / Mimir
browser ─────────HTTP:4318────▶ otel-collector
```

Para habilitar o envio, defina no `.env`:

```env
OTEL_TEMPO_ENDPOINT=http://IP-DO-GRAFANA:4318
VITE_OTEL_ENDPOINT=https://seu-dominio/otrs/otel
```

Rebuild (`VITE_OTEL_ENDPOINT` entra no build do frontend):

```bash
docker compose up -d --build
```

Consulta no Grafana Explore (Tempo):

```
{ resource.service.name = "otrs-mcp-api" }
```

Sem `OTEL_EXPORTER_OTLP_ENDPOINT` alcançável, o `opentelemetry-instrument` opera em modo noop. Sem `VITE_OTEL_ENDPOINT`, o frontend não envia traces.

---

## Deploy em produção

### Nginx

`nginx/mcp.conf` vem configurado para domínio compartilhado, servindo este projeto sob o subpath `/otrs/`:

| Rota | Destino |
|---|---|
| `/otrs/mcp` | `127.0.0.1:8001/mcp` (match exato, sem trailing slash) |
| `/otrs/api/` | `127.0.0.1:3000/api/` |
| `/otrs/otel/` | `127.0.0.1:4318/` |
| `/otrs/` | frontend |
| `/` | outro serviço em `127.0.0.1:9090` |

Ajuste `server_name` e, se for usar subpath, defina `VITE_BASE_PATH=/otrs/` antes do build do frontend. Depois:

```bash
sudo cp nginx/mcp.conf /etc/nginx/sites-available/mcp.conf
sudo ln -s /etc/nginx/sites-available/mcp.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d seu-dominio
```

> Confira a porta do frontend antes de recarregar: o Compose publica `127.0.0.1:8081`, e o vhost do repositório aponta para `8080`. Veja [Limitações conhecidas](#limitações-conhecidas).

### Systemd, backup e monitoramento

```bash
sudo cp deploy/otrs-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now otrs-mcp

chmod +x deploy/deploy.sh deploy/backup.sh deploy/healthcheck.sh
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/otrs-mcp-server/deploy/backup.sh") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/otrs-mcp-server/deploy/healthcheck.sh") | crontab -

sudo cp deploy/otrs-mcp.logrotate /etc/logrotate.d/otrs-mcp
```

Fail2ban:

```bash
sudo cp deploy/fail2ban/jail.local /etc/fail2ban/jail.local
sudo cp deploy/fail2ban/filter.d/* /etc/fail2ban/filter.d/
sudo systemctl restart fail2ban
```

Atualizações posteriores: `./deploy/deploy.sh --pull`.

---

## Estrutura do projeto

```
otrs-mcp-server/
├── src/otrs_mcp/
│   ├── main.py           # Entry point MCP (stdio / streamable-http)
│   ├── tools.py          # 5 tools MCP
│   ├── resources.py      # 3 resources MCP
│   ├── mcp_auth.py       # TokenVerifier de API key + escopos do MCP
│   ├── api.py            # API REST + middleware de security headers
│   ├── routes/admin.py   # Login, refresh, users, keys, auditoria, métricas
│   ├── auth.py           # JWT, API key, rate limit, permissões
│   ├── database.py       # SQLite WAL: schema e CRUD
│   ├── client.py         # Cliente HTTP do OTRS com sessão e retry
│   ├── config.py         # Configuração via pydantic-settings
│   ├── validation.py     # validate_ticket_id
│   ├── activity.py       # Atividade em JSON
│   ├── constants.py      # Prioridades e estados válidos
│   └── exceptions.py     # Exceções do domínio
├── frontend/             # React 19 + Vite 6 + Tailwind
├── nginx/mcp.conf        # Vhost do host
├── otel/                 # Config do collector
├── deploy/               # systemd, scripts, logrotate, fail2ban
├── tests/unit/           # 41 testes
├── docker-compose.yml
├── Dockerfile            # MCP server
└── Dockerfile.api        # API REST
```

### Tabelas do SQLite

| Tabela | Conteúdo |
|---|---|
| `admin_users` | Administradores e hash bcrypt |
| `api_keys` | Keys com hash, permissões, rate limit, expiração, contador de uso |
| `api_usage` | Auditoria de operações; base do rate limit e das métricas |
| `login_audit` | Tentativas de login; base do lockout de brute-force |

---

## Desenvolvimento

```bash
uv sync --extra dev

uv run pytest tests/unit/ -v
uv run pytest tests/unit/ --cov=src/otrs_mcp --cov-report=term-missing

uv run black src/
uv run isort src/
uv run mypy src/
```

Entry points instalados: `otrs-mcp-server` (MCP) e `otrs-mcp-api` (REST).

---

## Limitações conhecidas

Pontos que valem atenção antes de expor o serviço:

1. **Divergência de porta do frontend.** O Compose publica `127.0.0.1:8081:80`; o vhost faz `proxy_pass` para `127.0.0.1:8080`. Alinhe um dos dois, senão `/otrs/` responde 502.
2. **Rate limit conta operações registradas.** A janela usa as linhas de `api_usage`, gravadas pela API REST após o sucesso da operação. As tools MCP registram atividade em `activity.json`, não em `api_usage`, então o rate limit de uma key usada só via MCP não é acionado.
3. **`usage_count` infla no uso via MCP.** O token é validado em cada requisição HTTP do transporte streamable-http, e uma única sessão MCP gera várias requisições. O contador da key sobe mais rápido do que o número de tools chamadas.
4. **Lockout de login por IP e usuário.** Como a contagem considera o username, tentativas repetidas contra um usuário existente podem bloquear temporariamente o login legítimo dele. O desbloqueio é por tempo (15 min).
5. **SQLite sem criptografia em repouso.** Hashes de senha e de key ficam em `/data/otrs-mcp.db`. Proteja o volume e os backups.

---

## Solução de problemas

| Sintoma | O que verificar |
|---|---|
| Erro de SSL ao falar com o OTRS | `OTRS_VERIFY_SSL=false` para certificado interno |
| Redirect 301 do OTRS | Use a URL HTTPS completa em `OTRS_BASE_URL` |
| Start falha com `OTRSValidationError` | Falta `OTRS_BASE_URL`, `OTRS_USERNAME` ou `OTRS_PASSWORD` |
| Start falha pedindo JWT secret | `OTRS_ENV=production` exige `OTRS_JWT_SECRET` |
| Login sempre inválido no primeiro uso | Nenhum admin criado: defina `OTRS_ADMIN_PASSWORD` e recrie o container |
| `401` na API | Key revogada, expirada ou header ausente |
| `403` na API | Falta `read` ou `write` na key |
| `401` no `/mcp` | Cliente MCP sem `Authorization`, ou key inválida/revogada/vencida |
| `Permissao 'write' necessaria` na tool | A key só tem `read`; crie outra com `write` |
| MCP recusa toda key | O container `mcp-server` precisa do volume `app_data:/data` e de `OTRS_DB_PATH` para ler a tabela `api_keys` |
| `429` na API | Rate limit da key; aumente o valor ou use `0` |
| `429` no login | Lockout de brute-force; espere 15 min e confira o Login Audit |
| `422` em rota de ticket | `ticket_id` precisa ser só dígitos |
| `502` em `/otrs/` | Porta do frontend divergente (8080 vs 8081) |
| Traces ausentes no Grafana | Confira `OTEL_TEMPO_ENDPOINT` e `docker compose logs otel-collector` |
| SPA quebrada em subpath | Rebuild com `VITE_BASE_PATH` correto |

```bash
docker compose logs -f api
docker compose logs -f mcp-server
docker compose logs -f otel-collector
sudo journalctl -u otrs-mcp -f
sudo tail -f /var/log/nginx/mcp-admin-error.log
```

---

## Licença

Apache-2.0
