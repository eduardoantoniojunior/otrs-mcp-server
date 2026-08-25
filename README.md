# OTRS MCP Server

Servidor [Model Context Protocol][mcp] (MCP) para integracao com o [OTRS](https://otrs.org/) (Open Ticket Request System).

Permite que assistentes de IA (como o Claude Desktop) criem, consultem, busquem e atualizem tickets no OTRS por meio de uma interface padronizada. Inclui API REST autenticada, painel administrativo React e suporte a HTTPS automatico via Caddy.

[mcp]: https://modelcontextprotocol.io/introduction/introduction

---

## Sumario

- [Visao Geral da Arquitetura](#visao-geral-da-arquitetura)
- [Funcionalidades](#funcionalidades)
- [Pre-requisitos](#pre-requisitos)
- [Deploy](#deploy)
  - [Docker Compose (Recomendado)](#1-docker-compose-recomendado)
  - [Deploy Manual com HTTPS](#2-deploy-manual-com-https)
- [Configuracao](#configuracao)
  - [Variaveis de Ambiente](#variaveis-de-ambiente)
  - [Caddy (HTTPS)](#caddy-https)
  - [Usuarios Administradores](#usuarios-administradores)
  - [API Keys para Agentes](#api-keys-para-agentes)
- [Uso do MCP Server](#uso-do-mcp-server)
  - [Claude Desktop (Streamable HTTP)](#1-claude-desktop-streamable-http)
  - [Claude Desktop (stdio local)](#2-claude-desktop-stdio-local)
- [Referencia da API REST](#referencia-da-api-rest)
- [Referencia das Tools MCP](#referencia-das-tools-mcp)
- [Referencia dos Resources MCP](#referencia-dos-resources-mcp)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Desenvolvimento](#desenvolvimento)
- [Solucao de Problemas](#solucao-de-problemas)
- [Licenca](#licenca)

---

## Visao Geral da Arquitetura

```
┌──────────────────────┐
│   Agente Externo     │
│   (Claude Desktop)   │
└──────────┬───────────┘
           │ HTTPS + API Key
           ▼
┌──────────────────────┐
│    Caddy (:443)      │  HTTPS automatico (ACME/Let's Encrypt)
│    Reverse Proxy     │  Security headers (HSTS, CSP, etc)
└──┬───────────┬───────┘
   │           │
   │ /api/*    │ /mcp/*
   ▼           ▼
┌────────────┐  ┌────────────┐
│  API REST  │  │  MCP Server │
│ (FastAPI)  │  │ (FastMCP)   │
│   :3000    │  │   :8001     │
└─────┬──────┘  └──────┬──────┘
      │                │
      │   ┌────────────┘
      │   │
      ▼   ▼
┌──────────────────────┐
│   SQLite (WAL)       │
│   /data/otrs-mcp.db  │
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│   Servidor OTRS      │
│ (Generic Interface)  │
└──────────────────────┘

┌──────────────────────┐
│   Navegador Admin    │  Login + JWT
│   https://dominio    │
└──────────┬───────────┘
           │ HTTPS
           ▼
    Caddy → Frontend React + API REST
```

### Servicos Docker

| Servico | Tecnologia | Porta | Descricao |
|---|---|---|---|
| `caddy` | Caddy 2 | 80, 443 | Reverse proxy com HTTPS automatico |
| `api` | Python / FastAPI | 3000 (interno) | Backend REST + auth + SQLite |
| `mcp-server` | Python / FastMCP | 8001 (interno) | MCP Streamable HTTP |
| `frontend` | React / TypeScript | 80 (interno) | Dashboard administrativo |

---

## Funcionalidades

- Criar, buscar, visualizar e atualizar tickets no OTRS
- Acessar historico completo de tickets
- Autenticacao por API key para agentes externos
- Autenticacao JWT para painel administrativo
- Gerenciamento de API keys (criar, revogar, monitorar uso)
- Gerenciamento de usuarios administradores
- Dashboard com metricas de atividade
- HTTPS automatico via Caddy (ACME/Let's Encrypt)
- Security headers (HSTS, CSP, X-Frame-Options)
- Containerizacao com Docker Compose
- Retry automatico com backoff exponencial
- Gerenciamento automatico de sessoes no OTRS
- Dois modos de transporte: Streamable HTTP e stdio

---

## Pre-requisitos

### Configuracao do Servidor OTRS

#### Passo 1: Acessar o Painel Admin do OTRS

- URL: `https://seu-servidor-otrs/otrs/index.pl?Action=Admin`
- Faca login com suas credenciais de administrador

#### Passo 2: Configurar Web Services

1. Navegue ate: **Administracao do Sistema -> Web Services**
2. Crie ou verifique se existe um webservice com estas operacoes:
   - `SessionCreate`
   - `TicketCreate`
   - `TicketGet`
   - `TicketSearch`
   - `TicketUpdate`
   - `TicketHistoryGet`

#### Passo 3: Anotar a URL do Webservice

```
https://seu-servidor-otrs/otrs/nph-genericinterface.pl/Webservice/NomeDoWebservice
```

#### Passo 4: Garantir Permissoes do Usuario

Certifique-se de que o usuario OTRS possui permissoes para criar/atualizar tickets e usar a Generic Interface.

---

## Deploy

### 1. Docker Compose (Recomendado)

Metodo completo que sobe todos os 4 servicos (Caddy, API, MCP Server, Frontend).

#### Passo 1: Clonar o repositorio

```bash
git clone https://github.com/eduardoantoniojunior/otrs-mcp-server.git
cd otrs-mcp-server
```

#### Passo 2: Configurar variaveis de ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```env
# OTRS (obrigatorio)
OTRS_BASE_URL=https://seu-otrs.com/otrs/nph-genericinterface.pl/Webservice/TestInterface
OTRS_USERNAME=seu-usuario
OTRS_PASSWORD=sua-senha
OTRS_VERIFY_SSL=false

# JWT (obrigatorio para auth do frontend)
OTRS_JWT_SECRET=uma-senha-forte-de-pelo-menos-32-caracteres-aqui

# Admin padrao (mude a senha!)
OTRS_ADMIN_USER=admin
OTRS_ADMIN_PASSWORD=MUDE_ESTA_SENHA

# Dominio para HTTPS
EMAIL=seu-email@dominio.com
DOMAIN=otrs.seudominio.com
```

#### Passo 3: Configurar o Caddy

Edite `caddy/Caddyfile` se precisar de configuracoes customizadas. O padrao funciona para dominio unico.

#### Passo 4: Iniciar os servicos

```bash
docker compose up -d
```

#### Passo 5: Verificar

```bash
# Status dos servicos
docker compose ps

# Logs
docker compose logs -f

# Health check da API
curl https://otrs.seudominio.com/api/health
```

#### URLs de Acesso

| Servico | URL |
|---|---|
| Painel Administrativo | `https://otrs.seudominio.com` |
| API REST | `https://otrs.seudominio.com/api` |
| MCP Server | `https://otrs.seudominio.com/mcp` |

#### Comandos Uteis

```bash
# Parar
docker compose down

# Reconstruir
docker compose up -d --build

# Logs de um servico
docker compose logs -f api
docker compose logs -f caddy

# Reload do Caddy (sem downtime)
docker compose exec caddy caddy reload
```

### 2. Deploy Manual com HTTPS

Para deploy sem Docker Compose, usando cada componente separadamente.

#### API REST

```bash
pip install -e .
export OTRS_BASE_URL="https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/Test"
export OTRS_USERNAME="user"
export OTRS_PASSWORD="pass"
export OTRS_JWT_SECRET="sua-chave-secreta"
uvicorn otrs_mcp.api:app --host 0.0.0.0 --port 3000
```

#### MCP Server (Streamable HTTP)

```bash
export OTRS_MCP_TRANSPORT=http
export OTRS_MCP_PORT=8001
python -m otrs_mcp.main
```

#### MCP Server (stdio para Claude Desktop local)

```bash
python -m otrs_mcp.main
# O servidor roda via stdio, sem porta de rede
```

#### Frontend

```bash
cd frontend
npm ci
npm run build
# Servir dist/ com Caddy
```

---

## Configuracao

### Variaveis de Ambiente

#### OTRS (obrigatorio)

| Variavel | Descricao |
|---|---|
| `OTRS_BASE_URL` | URL completa do webservice OTRS |
| `OTRS_USERNAME` | Usuario do OTRS |
| `OTRS_PASSWORD` | Senha do OTRS |

#### OTRS (opcional)

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTRS_VERIFY_SSL` | `true` | Verificar certificados SSL |
| `OTRS_TIMEOUT` | `30` | Timeout HTTP em segundos |
| `OTRS_DEBUG` | `false` | Logging de debug |
| `OTRS_DEFAULT_QUEUE` | `Raw` | Fila padrao |
| `OTRS_DEFAULT_STATE` | `new` | Estado padrao |
| `OTRS_DEFAULT_PRIORITY` | `3 normal` | Prioridade padrao |
| `OTRS_DEFAULT_TYPE` | `Unclassified` | Tipo padrao |
| `OTRS_WEB_BASE_URL` | (derivado) | URL da interface web OTRS |

#### Autenticacao

| Variavel | Obrigatoria | Padrao | Descricao |
|---|---|---|---|
| `OTRS_JWT_SECRET` | Nao | (gerado) | Secret para assinatura JWT. Se nao definido, um segredo aleatorio e gerado (tokens nao persistem entre reinicios) |
| `OTRS_JWT_EXPIRE_MINUTES` | Nao | `480` | Tempo de vida do JWT (8 horas) |
| `OTRS_ADMIN_USER` | Nao | `admin` | Usuario admin padrao (criado na 1a execucao) |
| `OTRS_ADMIN_PASSWORD` | Sim | -- | Senha do admin padrao (criado na 1a execucao). **Obrigatorio definir!** |

#### MCP Server

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTRS_MCP_TRANSPORT` | `stdio` | Transporte: `stdio` ou `http` |
| `OTRS_MCP_HOST` | `0.0.0.0` | Host do MCP server (modo http) |
| `OTRS_MCP_PORT` | `8001` | Porta do MCP server (modo http) |

#### Banco de Dados e Atividade

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTRS_DB_PATH` | `/data/otrs-mcp.db` | Caminho do SQLite |
| `OTRS_ACTIVITY_FILE` | `/data/activity.json` | Arquivo de log de atividade MCP |
| `OTRS_ACTIVITY_MAX_EVENTS` | `1000` | Maximo de eventos no JSON |

#### CORS e Rede

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTRS_CORS_ORIGINS` | `http://localhost:5173,...` | Origens permitidas CORS |

### Caddy (HTTPS)

O Caddy configura HTTPS automaticamente via ACME (Let's Encrypt). Requisitos:

1. **DNS apontando** para o servidor
2. **Portas 80 e 443** abertas no firewall
3. **Variaveis de ambiente** `EMAIL` e `DOMAIN` definidas

Exemplo de `docker-compose.yml` para HTTPS:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    environment:
      - EMAIL=admin@seudominio.com
      - DOMAIN=otrs.seudominio.com
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # HTTP/3
```

Para **localhost/desenvolvimento**, o Caddy gera um certificado auto-assinado automaticamente.

### Usuarios Administradores

O primeiro usuario admin e criado automaticamente na primeira execucao, usando as variaveis `OTRS_ADMIN_USER` e `OTRS_ADMIN_PASSWORD`. A variavel `OTRS_ADMIN_PASSWORD` e obrigatoria — o servico nao inicia sem ela.

Acesse o painel em `https://seu-dominio` e faca login. Pelo painel voce pode:
- Criar novos usuarios administradores
- Gerenciar API keys dos agentes
- Monitorar atividade e uso

### API Keys para Agentes

API keys sao usadas por agentes externos (Claude Desktop, scripts, etc) para autenticar na API REST e no MCP Server.

#### Criar via Painel Administrativo

1. Faca login no painel (`https://seu-dominio`)
2. Navegue ate **API Keys**
3. Clique em **Nova Key**
4. Preencha:
   - **Nome**: identificacao amigavel (ex: "Claude Desktop - Joao")
   - **Nome do Agente**: identificador tecnico (ex: "claude-desktop-joao")
   - **Permissoes**: `read` e/ou `write`
   - **Expiracao**: opcional, em dias
5. Clique em **Criar**
6. **Guarde a chave mostrada!** Ela nao sera exibida novamente

#### Formato da Chave

```
sk-otrs-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

#### Uso

```bash
# Via header X-API-Key
curl -H "X-API-Key: sk-otrs-sua-chave" https://seu-dominio/api/tickets

# Via Authorization Bearer
curl -H "Authorization: Bearer sk-otrs-sua-chave" https://seu-dominio/api/tickets
```

---

## Uso do MCP Server

### 1. Claude Desktop (Streamable HTTP)

Recomendado para agentes remotos. Requer API key.

Edite `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "otrs": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote@0.1.38",
        "https://otrs.seudominio.com/mcp",
        "--header", "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "AUTH_HEADER": "Bearer sk-otrs-sua-chave-aqui"
      }
    }
  }
}
```

### 2. Claude Desktop (stdio local)

Para uso local sem HTTPS. Requer o servidor rodando localmente.

```json
{
  "mcpServers": {
    "otrs": {
      "command": "uv",
      "args": [
        "--directory", "/caminho/para/otrs-mcp-server",
        "run", "src/otrs_mcp/main.py"
      ],
      "env": {
        "OTRS_BASE_URL": "https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/Test",
        "OTRS_USERNAME": "seu-usuario",
        "OTRS_PASSWORD": "sua-senha",
        "OTRS_VERIFY_SSL": "false"
      }
    }
  }
}
```

> Se ver `Error: spawn uv ENOENT`, especifique o caminho completo para `uv`.

---

## Referencia da API REST

### Autenticacao

Os endpoints de tickets requerem autenticacao via header:

```
Authorization: Bearer <api-key-ou-jwt>
```

Endpoints de administracao (`/api/admin/*`) requerem JWT de admin.
Endpoints de tickets (`/api/tickets/*`) aceitam API key OU JWT de admin.

### Health Check (publico)

```
GET /api/health
```

### Tickets

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| `GET` | `/api/tickets` | API Key | Buscar tickets |
| `GET` | `/api/tickets/{id}` | API Key | Detalhes do ticket |
| `POST` | `/api/tickets` | API Key (write) | Criar ticket |
| `PUT` | `/api/tickets/{id}` | API Key (write) | Atualizar ticket |
| `GET` | `/api/tickets/{id}/history` | API Key | Historico do ticket |

### Activity

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| `GET` | `/api/activity` | API Key | Log de atividade |
| `GET` | `/api/activity/summary` | API Key | Resumo de metricas |
| `DELETE` | `/api/activity` | API Key (write) | Limpar atividade |

### Admin (requer JWT)

| Metodo | Rota | Auth | Descricao |
|---|---|---|---|
| `POST` | `/api/admin/login` | Publico | Login |
| `GET` | `/api/admin/me` | JWT | Dados do admin |
| `POST` | `/api/admin/users` | JWT | Criar admin |
| `GET` | `/api/admin/users` | JWT | Listar admins |
| `DELETE` | `/api/admin/users/{id}` | JWT | Remover admin |
| `POST` | `/api/admin/keys` | JWT | Criar API key |
| `GET` | `/api/admin/keys` | JWT | Listar keys |
| `PATCH` | `/api/admin/keys/{id}/revoke` | JWT | Revogar key |
| `DELETE` | `/api/admin/keys/{id}` | JWT | Remover key |
| `GET` | `/api/admin/activity` | JWT | Atividade dos agentes |

### Exemplos

```bash
# Login
curl -X POST https://seu-dominio/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","senha":"senha"}'

# Criar API key
curl -X POST https://seu-dominio/api/admin/keys \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Meu Agente","agent_name":"meu-agente","permissions":["read","write"]}'

# Listar tickets
curl -H "Authorization: Bearer sk-otrs-sua-chave" \
  https://seu-dominio/api/tickets?queue=Raw&limit=10

# Criar ticket
curl -X POST https://seu-dominio/api/tickets \
  -H "Authorization: Bearer sk-otrs-sua-chave" \
  -H "Content-Type: application/json" \
  -d '{"title":"Problema","body":"Descricao do problema"}'
```

---

## Referencia das Tools MCP

| Tool | Descricao | Parametros |
|---|---|---|
| `create_ticket` | Criar ticket | `title`, `body`, `queue?`, `priority?`, `state?`, `customer_user?`, `ticket_type?` |
| `get_ticket` | Detalhes do ticket | `ticket_id`, `include_dynamic_fields?`, `include_extended_data?` |
| `search_tickets` | Buscar tickets | `customer_user?`, `queue?`, `state?`, `priority?`, `title?`, `limit?`, `sort_by?`, `order_by?` |
| `update_ticket` | Atualizar ticket | `ticket_id`, `title?`, `queue?`, `priority?`, `state?`, `customer_user?`, `owner?` |
| `get_ticket_history` | Historico | `ticket_id` |

### Valores Validos

| Campo | Valores |
|---|---|
| Prioridade | `1 very low`, `2 low`, `3 normal`, `4 high`, `5 very high` |
| Fila | `Raw`, `Junk`, `Misc` |
| Estado | `new`, `open`, `closed successful`, `closed unsuccessful`, `pending reminder`, `pending auto close` |

---

## Referencia dos Resources MCP

| URI | Descricao |
|---|---|
| `otrs://ticket/{ticket_id}` | Dados do ticket em JSON |
| `otrs://ticket/{ticket_id}/history` | Historico do ticket |
| `otrs://search/tickets` | 20 tickets mais recentes |

---

## Estrutura do Projeto

```
otrs-mcp-server/
├── src/otrs_mcp/                # Pacote Python principal
│   ├── __init__.py              # API publica (v0.2.0)
│   ├── main.py                  # Entry point (MCP server stdio/http)
│   ├── config.py                # Configuracao (pydantic-settings)
│   ├── client.py                # Cliente HTTP com retry e sessao
│   ├── tools.py                 # Tools MCP (5 tools)
│   ├── resources.py             # Resources MCP (3 resources)
│   ├── api.py                   # Backend REST (FastAPI)
│   ├── auth.py                  # JWT + API key authentication
│   ├── database.py              # SQLite (schema + CRUD)
│   ├── activity.py              # Monitoramento de atividade (JSON)
│   ├── constants.py             # Filas, prioridades, estados
│   ├── exceptions.py            # Excecoes customizadas
│   └── routes/
│       ├── __init__.py
│       └── admin.py             # Rotas de autenticacao e gerenciamento
├── frontend/                    # Frontend React + TypeScript
│   ├── src/
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx   # Context de autenticacao
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx     # Tela de login
│   │   │   └── ApiKeysPage.tsx   # Gerenciamento de API keys
│   │   ├── components/
│   │   │   ├── Layout.tsx        # Layout com nav e logout
│   │   │   ├── Dashboard.tsx
│   │   │   ├── TicketList.tsx
│   │   │   ├── TicketDetail.tsx
│   │   │   └── TicketForm.tsx
│   │   ├── services/
│   │   │   └── api.ts            # HTTP client com auth
│   │   ├── App.tsx               # Rotas protegidas
│   │   └── main.tsx
│   ├── Dockerfile
│   └── Caddyfile
├── caddy/
│   └── Caddyfile                 # Configuracao do Caddy
├── tests/
│   ├── unit/                     # 42 testes unitarios
│   └── integration/              # Testes de integracao (OTRS real)
├── docker-compose.yml            # 4 servicos
├── Dockerfile                    # MCP server container
├── Dockerfile.api                # API REST container
├── pyproject.toml                # Dependencias e config
├── .env.example                  # Template de variaveis
└── PLANO_MELHORIAS.md            # Documento de referencia
```

---

## Desenvolvimento

### Instalacao

```bash
git clone https://github.com/eduardoantoniojunior/otrs-mcp-server.git
cd otrs-mcp-server

# Instalar UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Instalar dependencias
uv sync --python 3.12 --extra dev
```

### Testes

```bash
# Unitarios (42 testes)
uv run pytest tests/unit/ -v

# Com cobertura
uv run pytest tests/unit/ --cov=src/otrs_mcp --cov-report=term-missing

# Integracao (requer OTRS ativo)
uv run pytest tests/integration/ -v -m integration
```

### Formatacao

```bash
uv run black src/
uv run isort src/
uv run mypy src/
```

### Scripts CLI

```bash
# MCP server
otrs-mcp-server

# API REST
otrs-mcp-api
```

---

## Solucao de Problemas

### Erros Comuns

1. **SSL**: Defina `OTRS_VERIFY_SSL=false` para certificados auto-assinados
2. **HTTP 301**: Use URLs HTTPS se o OTRS redireciona
3. **Auth 401**: Verifique usuario/senha e configuracao do webservice
4. **Caddy 502**: Verifique se os containers `api` e `mcp-server` estao rodando

### Modo Debug

```bash
uv run python otrs_mcp_connectivity_test.py
```

### Logs

```bash
# Todos os servicos
docker compose logs -f

# Servico especifico
docker compose logs -f api
docker compose logs -f caddy
docker compose logs -f mcp-server
```

---

## Licenca

Apache-2.0

---

[mcp]: https://modelcontextprotocol.io
