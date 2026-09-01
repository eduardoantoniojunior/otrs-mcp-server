# OTRS MCP Server

Servidor [Model Context Protocol][mcp] (MCP) para integracao com o [OTRS](https://otrs.org/) (Open Ticket Request System).

Permite que assistentes de IA (como Claude Desktop, VS Code, agentes Python) criem, consultem, busquem e atualizem tickets no OTRS por meio de uma interface padronizada. Inclui API REST autenticada, painel administrativo React com dashboard de metricas, observabilidade via OpenTelemetry e deploy em producao com HTTPS, systemd, backup automatico e protecao contra ataques.

[mcp]: https://modelcontextprotocol.io/introduction/introduction

---

## Sumario

- [Arquitetura](#arquitetura)
- [Funcionalidades](#funcionalidades)
- [Pre-requisitos](#pre-requisitos)
- [Deploy](#deploy)
- [Deploy com Subpath](#deploy-com-subpath)
- [Producao](#producao)
- [Configuracao](#configuracao)
- [Uso do MCP Server](#uso-do-mcp-server)
- [Referencia da API REST](#referencia-da-api-rest)
- [Referencia das Tools MCP](#referencia-das-tools-mcp)
- [Referencia dos Resources MCP](#referencia-dos-resources-mcp)
- [Painel Administrativo](#painel-administrativo)
- [Seguranca](#seguranca)
- [Observabilidade (OpenTelemetry)](#observabilidade-opentelemetry)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Desenvolvimento](#desenvolvimento)
- [Solucao de Problemas](#solucao-de-problemas)
- [Licenca](#licenca)

---

## Arquitetura

```
┌──────────────────────────┐       ┌──────────────────────────┐
│   Agente IA              │       │   Navegador Admin        │
│ (Claude Desktop, Python) │       │ https://seu-dominio       │
└──────────┬───────────────┘       └──────────┬───────────────┘
           │ HTTPS + API Key                   │ HTTPS + JWT
           ▼                                   ▼
┌──────────────────────────────────────────────────────────────┐
│          Nginx (SSL via Certbot/Let's Encrypt)               │
│          + Fail2ban (protecao contra brute-force)            │
│          Porta 443 — Reverse Proxy                           │
└──────┬────────────────────┬────────────────────┬─────────────┘
       │ /mcp               │ /api/*             │ /
       ▼                    ▼                    ▼
┌────────────┐       ┌────────────┐       ┌────────────┐
│ MCP Server │       │  API REST  │       │  Frontend  │
│  (FastMCP) │       │ (FastAPI)  │       │  (React)   │
│ 127.0.0.1  │       │ 127.0.0.1  │       │ 127.0.0.1  │
│   :8001    │       │   :3000    │       │   :8080    │
└─────┬──────┘       └──────┬─────┘       └────────────┘
      │                     │
      └──────────┬──────────┘
                 ▼
      ┌──────────────────────┐       ┌──────────────────────┐
      │   SQLite (WAL)       │       │  OTel Collector       │
      │  /data/otrs-mcp.db   │       │  → Tempo / Mimir      │
      └──────────┬───────────┘       └───────────────────────┘
                 ▼
      ┌──────────────────────┐
      │   Servidor OTRS      │
      │ (Generic Interface)  │
      └──────────────────────┘
```

### Servicos Docker

| Servico | Tecnologia | Porta | CPU/Mem | Descricao |
|---|---|---|---|---|
| `api` | Python / FastAPI | 127.0.0.1:3000 | 1 CPU / 512M | Backend REST + auth + SQLite |
| `mcp-server` | Python / FastMCP | 127.0.0.1:8001 | 1 CPU / 512M | MCP Streamable HTTP |
| `frontend` | React / Nginx Alpine | 127.0.0.1:8080 | 0.5 CPU / 128M | Dashboard administrativo (SPA) |
| `otel-collector` | OTel Contrib | 127.0.0.1:4317-4318 | 0.5 CPU / 256M | Coleta traces e envia para Tempo/Mimir |

---

## Funcionalidades

### MCP Server
- Criar, buscar, visualizar e atualizar tickets no OTRS
- Acessar historico completo de tickets
- Transporte Streamable HTTP (remoto) e stdio (local)
- Retry automatico com backoff exponencial (3 tentativas)
- Gerenciamento automatico de sessoes OTRS com asyncio.Lock

### Seguranca
- Autenticacao por API key (`sk-otrs-...`) com SHA-256 hashing
- Autenticacao JWT (HS256, claims iat/jti/exp) para painel administrativo
- Token refresh automatico (renova 10 min antes de expirar)
- Rate limiting por API key (configuravel por token)
- Protecao brute-force no login (5 falhas em 15min = lockout, persistido no SQLite)
- Fail2ban no Nginx (bloqueia IPs com muitas falhas via iptables)
- Security headers (CSP, X-Frame-Options DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- CORS restrito (allow_headers limitado a Authorization + Content-Type)
- Validacao de entrada centralizada (ticket_id regex, Pydantic com min/max em todos os campos)
- Erros OTRS sanitizados (detalhes internos nao expostos ao cliente)
- HTTPS via Nginx + Certbot (Let's Encrypt)
- Containers Docker non-root, imagens pinadas, portas 127.0.0.1 only
- Limites de CPU/memoria por container

### Painel Administrativo
- Dashboard com graficos de atividade (barras por dia, ultimos 14 dias)
- Distribuicao de uso por tool e ranking de top agents
- Metricas: success rate, chamadas 24h, tokens ativos, logins falhados
- Alertas de seguranca (logins falhados, tokens expirando, tokens expirados, tokens nunca usados)
- Gerenciamento de API keys (criar, revogar, filtros, rate limit, indicadores de expiracao)
- Gerenciamento de usuarios administradores (com confirmacao de exclusao)
- Audit Log completo (todas as operacoes de ticket registram agent + api_key, filtros, export CSV/JSON)
- Login Audit (tentativas de login com IP, user agent, export CSV/JSON)
- Client MCP Wizard (configuracoes prontas para Claude Desktop, VS Code, Python, cURL)
- Pagina de configuracoes e status de conexao OTRS

### Observabilidade
- Auto-instrumentacao Python zero-code (FastAPI, httpx, SQLite3, logging) via `opentelemetry-instrument`
- Instrumentacao frontend (fetch, document load) via `@opentelemetry/sdk-trace-web`
- OTel Collector sidecar no Docker Compose para enviar traces para Tempo/Mimir
- Ativavel/desativavel via variaveis de ambiente (sem overhead quando desabilitado)

### Infraestrutura de Producao
- Systemd service (boot automatico, restart on failure)
- Script de deploy (git pull + build + healthcheck + limpeza de imagens)
- Backup automatico do SQLite (diario, 7 dias de retencao, compressao gzip)
- Log rotation para Docker
- Health check externo com webhook de alerta (Slack/Discord/Teams)
- Suporte a subpath para dominio compartilhado entre multiplos MCPs

---

## Pre-requisitos

- **Docker** e **Docker Compose** instalados no servidor
- **Nginx** instalado no servidor host (para reverse proxy HTTPS)
- **Certbot** instalado (para certificado SSL Let's Encrypt)
- **Dominio** apontando para o IP do servidor (registro A no DNS)
- Servidor OTRS com **Generic Interface** configurada

### Configuracao do OTRS

1. Acesse **Administracao -> Web Services** no OTRS
2. Crie/verifique um webservice com estas operacoes:
   - `SessionCreate`, `TicketCreate`, `TicketGet`, `TicketSearch`, `TicketUpdate`, `TicketHistoryGet`
3. Anote a URL: `https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/NomeDoWebservice`
4. Garanta que o usuario tem permissoes para tickets e Generic Interface

---

## Deploy

### 1. Clonar e configurar

```bash
git clone https://github.com/eduardoantoniojunior/otrs-mcp-server.git
cd otrs-mcp-server
cp .env.example .env
```

Edite o `.env`:

```env
# OTRS (obrigatorio)
OTRS_BASE_URL=https://seu-otrs/otrs/nph-genericinterface.pl/Webservice/MCPConnector
OTRS_USERNAME=seu-usuario
OTRS_PASSWORD=sua-senha

# Seguranca (obrigatorio em producao)
OTRS_ENV=production
OTRS_JWT_SECRET=gere-com-python-c-import-secrets-print-secrets-token-hex-32
OTRS_ADMIN_USER=admin
OTRS_ADMIN_PASSWORD=MUDE_ESTA_SENHA

# CORS (ajuste para seu dominio)
OTRS_CORS_ORIGINS=https://seu-dominio
```

### 2. Subir os containers

```bash
docker compose up -d --build
```

Verifique:

```bash
docker compose ps
curl -s http://127.0.0.1:3000/api/health
curl -s http://127.0.0.1:8080 | head -5
```

### 3. Configurar Nginx (HTTPS)

Edite `nginx/mcp.conf` e substitua `SEU_DOMINIO` pelo seu dominio real. Depois:

```bash
sudo cp nginx/mcp.conf /etc/nginx/sites-available/mcp.conf
sudo ln -s /etc/nginx/sites-available/mcp.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d seu-dominio
```

### 4. Verificar

```bash
curl https://seu-dominio/api/health
```

### URLs de acesso

| Servico | URL |
|---|---|
| Painel Administrativo | `https://seu-dominio` |
| API REST | `https://seu-dominio/api` |
| MCP Endpoint | `https://seu-dominio/mcp` |

---

## Deploy com Subpath

Quando varios MCPs compartilham o mesmo dominio, cada um pode ficar num subpath diferente.

Exemplo: `https://mcp.dominio.com/otrs/`

### Como ativar

1. No `.env`, defina o subpath:

```env
VITE_BASE_PATH=/otrs/
```

2. Rebuild o frontend (o subpath e aplicado no build):

```bash
docker compose build frontend
docker compose up -d
```

3. No `nginx/mcp.conf`:
   - Comente todo o **MODO 1** (dominio dedicado)
   - Descomente todo o **MODO 2** (subpath)
   - Substitua `/otrs` pelo subpath desejado

4. Recarregue o Nginx:

```bash
sudo cp nginx/mcp.conf /etc/nginx/sites-available/mcp.conf
sudo nginx -t && sudo systemctl reload nginx
```

### URLs com subpath

| Servico | URL |
|---|---|
| Painel Administrativo | `https://mcp.dominio.com/otrs/` |
| API REST | `https://mcp.dominio.com/otrs/api/` |
| MCP Endpoint | `https://mcp.dominio.com/otrs/mcp` |

### Como desativar (voltar para dominio dedicado)

1. Remova `VITE_BASE_PATH` do `.env` (ou defina como `/`)
2. Rebuild: `docker compose build frontend && docker compose up -d`
3. No `nginx/mcp.conf`, comente MODO 2 e descomente MODO 1

---

## Producao

### 5. Instalar como servico systemd

```bash
sudo cp deploy/otrs-mcp.service /etc/systemd/system/otrs-mcp.service
sudo systemctl daemon-reload
sudo systemctl enable otrs-mcp
sudo systemctl start otrs-mcp
```

Comandos:

```bash
sudo systemctl status otrs-mcp              # Status
sudo systemctl restart otrs-mcp             # Restart
sudo journalctl -u otrs-mcp -f              # Logs tempo real
sudo journalctl -u otrs-mcp --since "1h"    # Logs recentes
```

### 6. Configurar Fail2ban

```bash
sudo apt install fail2ban
sudo cp deploy/fail2ban/jail.local /etc/fail2ban/jail.local
sudo cp deploy/fail2ban/filter.d/* /etc/fail2ban/filter.d/
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

Jails configuradas:

| Jail | Trigger | Ban |
|------|---------|-----|
| `otrs-mcp-login` | 5 falhas de login em 5 min | 15 min |
| `otrs-mcp-api` | 20 erros 401/403 em 1 min | 10 min |
| `nginx-botsearch` | 10 scans (wp-admin, .env, .git) em 5 min | 1 hora |

Verificar:

```bash
sudo fail2ban-client status                           # Listar jails
sudo fail2ban-client status otrs-mcp-login            # IPs banidos
sudo fail2ban-client set otrs-mcp-login unbanip 1.2.3.4  # Desbanir
```

### 7. Configurar backup automatico

```bash
chmod +x deploy/deploy.sh deploy/backup.sh deploy/healthcheck.sh

# Backup diario as 3h
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/otrs-mcp-server/deploy/backup.sh >> /var/log/otrs-mcp-backup.log 2>&1") | crontab -

# Health check a cada 5 minutos
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/otrs-mcp-server/deploy/healthcheck.sh") | crontab -
```

Backup: SQLite consistente via `sqlite3.backup()`, compressao gzip, retencao 7 dias.

### 8. Configurar log rotation

```bash
sudo cp deploy/otrs-mcp.logrotate /etc/logrotate.d/otrs-mcp
```

Ou globalmente no Docker (`/etc/docker/daemon.json`):

```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
```

### 9. Health check com alertas (opcional)

Configure `HEALTHCHECK_WEBHOOK_URL` no `.env` para receber alertas via webhook quando um servico cair:

```env
HEALTHCHECK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
```

O script `deploy/healthcheck.sh` verifica API, MCP e Frontend a cada 5 min, envia alerta na primeira falha e notifica recuperacao.

### Script de deploy

Para atualizacoes futuras:

```bash
./deploy/deploy.sh --pull    # Git pull + build + restart + healthcheck
./deploy/deploy.sh           # Apenas rebuild + restart
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
| `OTRS_DEFAULT_QUEUE` | `Raw` | Fila padrao para tickets |
| `OTRS_DEFAULT_STATE` | `new` | Estado padrao |
| `OTRS_DEFAULT_PRIORITY` | `3 normal` | Prioridade padrao |
| `OTRS_DEFAULT_TYPE` | `` | Tipo padrao |
| `OTRS_WEB_BASE_URL` | (derivado) | URL da interface web OTRS |
| `OTRS_VALID_QUEUES` | `` | Filas validas (dropdown no painel, separadas por virgula) |
| `OTRS_VALID_TYPES` | `` | Tipos validos (dropdown no painel, separados por virgula) |

#### Autenticacao

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTRS_ENV` | `development` | Ambiente (`production` exige JWT_SECRET) |
| `OTRS_JWT_SECRET` | (gerado) | Secret para assinatura JWT (min 32 chars) |
| `OTRS_JWT_EXPIRE_MINUTES` | `480` | Tempo de vida do JWT (8 horas) |
| `OTRS_ADMIN_USER` | `admin` | Usuario admin padrao |
| `OTRS_ADMIN_PASSWORD` | -- | Senha do admin padrao (**obrigatorio**) |

#### MCP Server

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTRS_MCP_TRANSPORT` | `stdio` | Transporte: `stdio` ou `http` |
| `OTRS_MCP_HOST` | `0.0.0.0` | Host do MCP server (modo http) |
| `OTRS_MCP_PORT` | `8001` | Porta do MCP server (modo http) |

#### Banco de Dados

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTRS_DB_PATH` | `/data/otrs-mcp.db` | Caminho do SQLite |
| `OTRS_ACTIVITY_FILE` | `/data/activity.json` | Log de atividade MCP |
| `OTRS_ACTIVITY_MAX_EVENTS` | `1000` | Maximo de eventos no JSON |

#### CORS

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTRS_CORS_ORIGINS` | `http://localhost:5173,...` | Origens permitidas (separadas por virgula) |

#### Frontend

| Variavel | Padrao | Descricao |
|---|---|---|
| `VITE_BASE_PATH` | `/` | Subpath do deploy (ex: `/otrs/` para dominio compartilhado) |

#### OpenTelemetry (opcional)

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTEL_TEMPO_ENDPOINT` | -- | URL OTLP HTTP do Tempo/Mimir (ex: `http://172.31.x.x:4318`) |
| `VITE_OTEL_ENDPOINT` | -- | URL publica do collector para browser traces (ex: `https://seu-dominio/otel`) |

### API Keys

API keys autenticam agentes externos (Claude Desktop, bou-vigilante, scripts).

**Criar via painel:**
1. Login em `https://seu-dominio`
2. Ir em **MCP Tokens**
3. Clicar em **Create Token**
4. Definir nome, agent, permissoes (`read`/`write`), rate limit e expiracao
5. Copiar a chave gerada (exibida apenas uma vez)

**Formato:** `sk-otrs-{64 caracteres hex}`

**Rate Limit:** Configuravel por token (requests/minuto). Use `0` para ilimitado (recomendado para agentes automatizados).

---

## Uso do MCP Server

### Claude Desktop (Streamable HTTP remoto)

```json
{
  "mcpServers": {
    "otrs": {
      "url": "https://seu-dominio/mcp",
      "headers": {
        "Authorization": "Bearer sk-otrs-sua-api-key-aqui"
      }
    }
  }
}
```

Se usando subpath:

```json
{
  "mcpServers": {
    "otrs": {
      "url": "https://mcp.dominio.com/otrs/mcp",
      "headers": {
        "Authorization": "Bearer sk-otrs-sua-api-key-aqui"
      }
    }
  }
}
```

### VS Code / Kiro

```json
{
  "servers": {
    "otrs": {
      "type": "http",
      "url": "https://seu-dominio/mcp",
      "headers": {
        "Authorization": "Bearer sk-otrs-sua-api-key-aqui"
      }
    }
  }
}
```

### Python SDK

```python
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

async def main():
    headers = {"Authorization": "Bearer sk-otrs-sua-api-key"}
    async with streamablehttp_client(
        "https://seu-dominio/mcp", headers=headers
    ) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool(
                "search_tickets",
                arguments={"state": "new", "limit": 5}
            )
```

### stdio (local, sem rede)

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

---

## Referencia da API REST

### Autenticacao

Todos os endpoints (exceto `/api/health`) requerem:

```
Authorization: Bearer <api-key-ou-jwt>
```

- Endpoints de tickets: API key ou JWT
- Endpoints admin (`/api/admin/*`): apenas JWT

### Endpoints

#### Publico

| Metodo | Rota | Descricao |
|---|---|---|
| `GET` | `/api/health` | Health check |

#### Tickets (API key ou JWT)

| Metodo | Rota | Permissao | Descricao |
|---|---|---|---|
| `GET` | `/api/tickets` | read | Buscar tickets (filtros: queue, state, priority, title, customer_user, customer_id) |
| `GET` | `/api/tickets/{id}` | read | Detalhes do ticket |
| `POST` | `/api/tickets` | write | Criar ticket |
| `PUT` | `/api/tickets/{id}` | write | Atualizar ticket |
| `GET` | `/api/tickets/{id}/history` | read | Historico do ticket |

#### Atividade (API key ou JWT)

| Metodo | Rota | Permissao | Descricao |
|---|---|---|---|
| `GET` | `/api/activity` | read | Log de atividade |
| `GET` | `/api/activity/summary` | read | Resumo de metricas |
| `DELETE` | `/api/activity` | write | Limpar atividade |

#### Configuracao (API key ou JWT)

| Metodo | Rota | Descricao |
|---|---|---|
| `GET` | `/api/config` | Filas e tipos validos |

#### Administracao (apenas JWT)

| Metodo | Rota | Descricao |
|---|---|---|
| `POST` | `/api/admin/login` | Login (retorna JWT) |
| `POST` | `/api/admin/refresh` | Renovar JWT (token refresh) |
| `GET` | `/api/admin/me` | Dados do admin logado |
| `POST` | `/api/admin/users` | Criar admin |
| `GET` | `/api/admin/users` | Listar admins |
| `DELETE` | `/api/admin/users/{id}` | Remover admin |
| `POST` | `/api/admin/keys` | Criar API key |
| `GET` | `/api/admin/keys` | Listar API keys |
| `PATCH` | `/api/admin/keys/{id}/revoke` | Revogar key |
| `DELETE` | `/api/admin/keys/{id}` | Remover key |
| `GET` | `/api/admin/activity` | Atividade detalhada dos agentes |
| `GET` | `/api/admin/login-audit` | Log de tentativas de login |
| `GET` | `/api/admin/metrics/daily` | Metricas diarias (graficos dashboard) |

---

## Referencia das Tools MCP

| Tool | Descricao | Parametros |
|---|---|---|
| `create_ticket` | Criar ticket | `title`, `body`, `queue?`, `priority?`, `state?`, `customer_user?`, `ticket_type?` |
| `get_ticket` | Detalhes do ticket | `ticket_id`, `include_dynamic_fields?`, `include_extended_data?` |
| `search_tickets` | Buscar tickets | `customer_user?`, `customer_id?`, `queue?`, `state?`, `priority?`, `title?`, `limit?`, `sort_by?`, `order_by?` |
| `update_ticket` | Atualizar ticket | `ticket_id`, `title?`, `queue?`, `priority?`, `state?`, `customer_user?`, `owner?` |
| `get_ticket_history` | Historico | `ticket_id` |

---

## Referencia dos Resources MCP

| URI | Descricao |
|---|---|
| `otrs://ticket/{ticket_id}` | Dados do ticket em JSON |
| `otrs://ticket/{ticket_id}/history` | Historico do ticket |
| `otrs://search/tickets` | 20 tickets mais recentes |

---

## Painel Administrativo

| Pagina | Funcionalidade |
|---|---|
| **Dashboard** | Graficos de atividade (barras 14 dias), distribuicao por tool, ranking top agents, metricas 24h, success rate, alertas de seguranca |
| **MCP Tokens** | CRUD de API keys com filtros (busca, permissao, status), rate limit, indicadores de expiracao/never used, confirmacao detalhada |
| **Admin Users** | Gerenciamento de administradores com confirmacao de exclusao |
| **Client MCP Wizard** | Configuracoes prontas para Claude Desktop, VS Code, cURL, Python SDK |
| **Audit Log** | Log completo de todas as operacoes (agent, api_key, ticket_id, duracao), filtros e export CSV/JSON |
| **Login Audit** | Tentativas de login (sucesso/falha, IP, user agent), stats, export CSV/JSON |
| **Settings** | Status de conexao OTRS, filas e tipos configurados, versao do servidor |

---

## Seguranca

### Camadas de protecao

| Camada | Implementacao |
|---|---|
| **Rede** | Portas Docker em 127.0.0.1 only, Nginx com HTTPS (Certbot), `/mcp` exige Authorization header |
| **Firewall** | Fail2ban com 3 jails: login brute-force, API abuse, bot/scanner detection |
| **Autenticacao** | JWT (HS256 + iat/jti) para admin, API keys (SHA-256) para agentes, dual auth nos endpoints |
| **Brute-force** | 5 falhas em 15min = lockout por IP e username, persistido no SQLite |
| **Rate limiting** | Por API key, configuravel (requests/minuto) |
| **Headers HTTP** | CSP, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy, Permissions-Policy |
| **CORS** | Origins configuravel, allow_headers restrito a Authorization + Content-Type |
| **Validacao** | ticket_id regex centralizado, Pydantic com min/max em todos os campos, erros OTRS sanitizados |
| **Docker** | Non-root (user otrs), multi-stage build, imagens pinadas (python:3.12.8, nginx:1.27, uv:0.5) |
| **Recursos** | Limites CPU/memoria por container, request body size limit (1MB no Nginx) |
| **Auditoria** | Todas as operacoes de ticket registram agent + api_key no SQLite, login audit com IP e user agent |
| **Frontend** | JWT expirado validado no bootstrap, token refresh automatico, ErrorBoundary, cache limpo no logout, AbortController timeout |

---

## Observabilidade (OpenTelemetry)

O projeto inclui instrumentacao completa via OpenTelemetry para traces e metricas.

### Arquitetura

```
Backend (api/mcp) ──[gRPC:4317]──→ OTel Collector ──[OTLP HTTP]──→ Tempo/Mimir
Frontend (browser) ──[HTTP:4318]──→ OTel Collector ──[OTLP HTTP]──→ Tempo/Mimir
```

### O que e instrumentado

| Componente | Instrumentacao | Tipo |
|---|---|---|
| **API REST** | FastAPI, httpx, SQLite3, logging | Zero-code (`opentelemetry-instrument`) |
| **MCP Server** | httpx, logging | Zero-code (`opentelemetry-instrument`) |
| **Frontend** | fetch (API calls), document load | SDK (`@opentelemetry/sdk-trace-web`) |

### Habilitar

1. No `.env`, defina o endpoint do seu Tempo:

```env
OTEL_TEMPO_ENDPOINT=http://172.31.x.x:4318
VITE_OTEL_ENDPOINT=https://seu-dominio/otel
```

2. Rebuild e restart:

```bash
docker compose down
docker compose up -d --build
```

3. Copiar o nginx atualizado (tem o proxy `/otel/` para o collector):

```bash
sudo cp nginx/mcp.conf /etc/nginx/sites-available/mcp.conf
sudo nginx -t && sudo systemctl reload nginx
```

4. Verificar no Grafana Explore (Tempo):

```
TraceQL: { resource.service.name = "otrs-mcp-api" }
```

### Desabilitar

Se `OTEL_TEMPO_ENDPOINT` nao estiver definido, o collector opera sem destino.

Se `VITE_OTEL_ENDPOINT` nao estiver definido, o frontend nao envia traces.

O `opentelemetry-instrument` opera em modo noop quando nao ha exporter configurado (sem overhead).

---

## Estrutura do Projeto

```
otrs-mcp-server/
├── src/otrs_mcp/                # Pacote Python principal
│   ├── __init__.py              # API publica (v0.2.0)
│   ├── main.py                  # Entry point MCP (stdio/http)
│   ├── config.py                # Configuracao (pydantic-settings)
│   ├── client.py                # Cliente HTTP OTRS com retry + asyncio.Lock
│   ├── tools.py                 # 5 Tools MCP com validacao
│   ├── resources.py             # 3 Resources MCP
│   ├── api.py                   # Backend REST (FastAPI) com audit trail
│   ├── auth.py                  # JWT (iat/jti) + API key + rate limiting
│   ├── database.py              # SQLite WAL (schema + CRUD + metricas diarias)
│   ├── validation.py            # Validacao centralizada (ticket_id)
│   ├── activity.py              # Monitoramento de atividade (JSON)
│   ├── constants.py             # Prioridades e estados validos
│   ├── exceptions.py            # Excecoes customizadas
│   └── routes/
│       └── admin.py             # Login (brute-force SQLite), refresh, keys, users, audit, metrics
├── frontend/                    # React 19 + TypeScript + TailwindCSS
│   ├── src/
│   │   ├── pages/               # Login, ApiKeys, AuditLog, LoginAudit, Settings, ClientWizard
│   │   ├── components/          # Dashboard (graficos CSS), Layout
│   │   ├── contexts/            # AuthContext (JWT refresh automatico)
│   │   ├── hooks/               # useTickets, useHealth, etc.
│   │   ├── services/api.ts      # HTTP client (timeout, logout centralizado, subpath-aware)
│   │   ├── telemetry.ts         # OpenTelemetry Web SDK (fetch + document load)
│   │   └── types/               # TypeScript types
│   ├── Dockerfile               # Node 20 build + Nginx 1.27 Alpine serve
│   ├── nginx.conf               # Security headers (CSP, X-Frame-Options, etc.)
│   ├── vite.config.ts           # Vite config (base path via VITE_BASE_PATH)
│   └── package.json             # React 19, Vite 6, TanStack Query 5, OTel Web SDK
├── nginx/
│   └── mcp.conf                 # Nginx vhost (MODO 1: raiz, MODO 2: subpath comentado)
├── otel/
│   └── otel-collector.yaml      # Config OTel Collector (OTLP → Tempo/Mimir)
├── deploy/
│   ├── otrs-mcp.service         # Systemd service unit
│   ├── deploy.sh                # Script deploy (pull + build + healthcheck)
│   ├── backup.sh                # Backup SQLite (sqlite3.backup, gzip, 7 dias)
│   ├── healthcheck.sh           # Health check externo com webhook de alerta
│   ├── otrs-mcp.logrotate       # Log rotation para Docker
│   └── fail2ban/
│       ├── jail.local           # Config fail2ban (3 jails)
│       └── filter.d/
│           ├── otrs-mcp-login.conf    # Filtro login brute-force
│           ├── otrs-mcp-api.conf      # Filtro API abuse
│           └── nginx-botsearch.conf   # Filtro bot/scanner
├── tests/
│   ├── unit/                    # 41 testes unitarios (pytest)
│   └── integration/             # Testes de integracao
├── docker-compose.yml           # 4 servicos (api, mcp, frontend, otel-collector)
├── Dockerfile                   # MCP server (python:3.12.8, non-root, OTel zero-code)
├── Dockerfile.api               # API REST (python:3.12.8, non-root, OTel zero-code)
├── pyproject.toml               # Dependencias, build, CLI scripts
├── .env.example                 # Template de variaveis
└── AGENTS.md                    # Guia para agentes de IA
```

---

## Desenvolvimento

### Setup local

```bash
git clone https://github.com/eduardoantoniojunior/otrs-mcp-server.git
cd otrs-mcp-server

# Python (backend)
uv sync --extra dev

# Frontend
cd frontend && npm ci
```

### Testes

```bash
# Unitarios (41 testes)
uv run pytest tests/unit/ -v

# Com cobertura
uv run pytest tests/unit/ --cov=src/otrs_mcp --cov-report=term-missing
```

### Formatacao e lint

```bash
uv run black src/
uv run isort src/
uv run mypy src/
```

### Rodar local (desenvolvimento)

```bash
# API REST (porta 3000)
uv run uvicorn otrs_mcp.api:app --port 3000 --reload

# MCP Server (porta 8001)
OTRS_MCP_TRANSPORT=http uv run python -m otrs_mcp.main

# Frontend (porta 5173, hot reload)
cd frontend && npm run dev
```

### CLI entry points

```bash
otrs-mcp-server   # Inicia o MCP server
otrs-mcp-api      # Inicia a API REST
```

---

## Solucao de Problemas

| Problema | Solucao |
|---|---|
| SSL error ao conectar no OTRS | Defina `OTRS_VERIFY_SSL=false` |
| HTTP 301 redirect | Use URL HTTPS completa no `OTRS_BASE_URL` |
| Auth 401 na API | Verifique API key (ativa? expirada? permissoes?) |
| Rate limit 429 | Aumente o rate limit do token ou use `rate_limit: 0` |
| Login bloqueado (429) | Brute-force lockout. Espere 15 min ou verifique no Login Audit |
| MCP connection refused | Verifique se o container `mcp-server` esta rodando |
| Frontend 404 no F5 | Verifique que o Nginx faz proxy para a porta 8080 |
| Certificado SSL expirado | Execute `sudo certbot renew` |
| IP banido pelo fail2ban | `sudo fail2ban-client set otrs-mcp-login unbanip <IP>` |
| Container sem memoria | Ajuste limites em `docker-compose.yml` (deploy.resources.limits) |
| Traces nao aparecem no Grafana | Verifique `OTEL_TEMPO_ENDPOINT` e `docker compose logs otel-collector` |
| Frontend com subpath errado | Verifique `VITE_BASE_PATH` no `.env` e rebuild: `docker compose build frontend` |

### Logs

```bash
docker compose logs -f                # Todos os containers
docker compose logs -f api            # API REST
docker compose logs -f mcp-server     # MCP Server
docker compose logs -f frontend       # Frontend
docker compose logs -f otel-collector # OpenTelemetry Collector
sudo journalctl -u otrs-mcp -f       # Systemd service
sudo tail -f /var/log/nginx/error.log          # Nginx
sudo fail2ban-client status otrs-mcp-login     # Fail2ban
```

---

## Licenca

Apache-2.0
