# OTRS MCP Server

Servidor [Model Context Protocol][mcp] (MCP) para integracao com o [OTRS](https://otrs.org/) (Open Ticket Request System).

Permite que assistentes de IA (como o Claude Desktop) criem, consultem, busquem e atualizem tickets no OTRS por meio de uma interface padronizada. O projeto tambem inclui uma API REST e um dashboard React para gerenciamento de tickets.

[mcp]: https://modelcontextprotocol.io/introduction/introduction

---

## Sumario

- [Visao Geral da Arquitetura](#visao-geral-da-arquitetura)
- [Funcionalidades](#funcionalidades)
- [Pre-requisitos](#pre-requisitos)
- [Deploy](#deploy)
  - [Docker Compose (Recomendado)](#1-docker-compose-recomendado)
  - [Docker (Somente MCP Server)](#2-docker-somente-mcp-server)
  - [Ambiente Local com UV](#3-ambiente-local-com-uv)
- [Referencia da API REST](#referencia-da-api-rest)
- [Referencia das Tools MCP](#referencia-das-tools-mcp)
- [Referencia dos Resources MCP](#referencia-dos-resources-mcp)
- [Variaveis de Ambiente](#variaveis-de-ambiente)
- [Desenvolvimento](#desenvolvimento)
- [Solucao de Problemas](#solucao-de-problemas)
- [Licenca](#licenca)

---

## Visao Geral da Arquitetura

O projeto possui tres componentes que podem ser executados juntos ou separadamente:

```
┌─────────────────────┐
│   Claude Desktop /   │
│   Assistente de IA   │
└─────────┬───────────┘
          │ stdio (MCP Protocol)
          ▼
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│    MCP Server       │────▶│     API REST        │────▶│    Servidor OTRS    │
│   (Python/FastMCP)  │     │   (FastAPI :3000)   │     │   (Generic Interface)│
└─────────────────────┘     └─────────┬───────────┘     └─────────────────────┘
                                      │
                                      ▼
                            ┌─────────────────────┐
                            │   Frontend React     │
                            │   (Vite + nginx)     │
                            │      :8080           │
                            └─────────────────────┘
```

| Componente | Tecnologia | Porta | Descricao |
|---|---|---|---|
| **MCP Server** | Python / FastMCP | stdio | Servidor MCP para integracao com assistentes de IA |
| **API REST** | Python / FastAPI | 3000 | Backend REST para aplicacoes web |
| **Frontend** | React / TypeScript / Vite | 8080 | Dashboard com metricas e gerenciamento de tickets |

---

## Funcionalidades

- Criar, buscar, visualizar e atualizar tickets no OTRS
- Acessar historico completo de tickets
- Configuracao de valores padrao (fila, estado, prioridade, tipo)
- Suporte a SSL/TLS com verificacao de certificados
- Monitoramento de atividade (chamadas de tools, taxas de sucesso/erro, duracao)
- Dashboard React com metricas em tempo real
- Containerizacao com Docker e Docker Compose
- Retry automatico com backoff exponencial para chamadas HTTP
- Gerenciamento automatico de sessoes no OTRS

---

## Pre-requisitos

### Configuracao do Servidor OTRS

Antes de usar este servidor MCP, configure sua instancia OTRS:

#### Passo 1: Acessar o Painel Admin do OTRS

- URL: `https://seu-servidor-otrs/otrs/index.pl?Action=Admin`
- Faca login com suas credenciais de administrador

#### Passo 2: Configurar Web Services

1. Navegue ate: **Administracao do Sistema -> Web Services**
2. Crie ou verifique se existe um webservice (ex: "TestInterface") com estas operacoes:
   - `SessionCreate` -- Criacao de sessao
   - `TicketCreate` -- Criacao de tickets
   - `TicketGet` -- Detalhes do ticket
   - `TicketSearch` -- Busca de tickets
   - `TicketUpdate` -- Atualizacao de tickets
   - `TicketHistoryGet` -- Historico do ticket

#### Passo 3: Anotar a URL do Webservice

A URL do webservice deve ter este formato:

```
https://seu-servidor-otrs/otrs/nph-genericinterface.pl/Webservice/NomeDoWebservice
```

#### Passo 4: Garantir Permissoes do Usuario

Certifique-se de que o usuario OTRS possui permissoes para:

- Criar e atualizar tickets
- Acessar itens de configuracao
- Usar a Interface Generica

### Operacoes do Web Service OTRS

| Operacao | Controller | Descricao |
|---|---|---|
| SessionCreate | Session::SessionCreate | Criar sessao autenticada |
| TicketCreate | Ticket::TicketCreate | Criar novos tickets |
| TicketGet | Ticket::TicketGet | Obter detalhes do ticket |
| TicketSearch | Ticket::TicketSearch | Buscar tickets |
| TicketUpdate | Ticket::TicketUpdate | Atualizar tickets existentes |
| TicketHistoryGet | Ticket::TicketHistoryGet | Obter historico do ticket |

---

## Deploy

### 1. Docker Compose (Recomendado)

O metodo mais completo, que sobe todos os componentes (API REST, Frontend e MCP Server) de uma vez.

#### Passo 1: Clonar o repositorio

```bash
git clone https://github.com/eduardoantoniojunior/otrs-mcp-server.git
cd otrs-mcp-server
```

#### Passo 2: Configurar as variaveis de ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```env
OTRS_BASE_URL=https://seu-servidor-otrs/otrs/nph-genericinterface.pl/Webservice/TestInterface
OTRS_USERNAME=seu-usuario
OTRS_PASSWORD=sua-senha
OTRS_VERIFY_SSL=false
OTRS_DEFAULT_QUEUE=Raw
OTRS_DEFAULT_STATE=new
OTRS_DEFAULT_PRIORITY=3 normal
```

#### Passo 3: Iniciar os servicos

```bash
docker compose up -d
```

#### Passo 4: Verificar os servicos

```bash
# Verificar status
docker compose ps

# Verificar logs
docker compose logs -f

# Verificar saude da API
curl http://localhost:3000/api/health
```

Os servicos ficarao disponiveis em:

| Servico | URL |
|---|---|
| Frontend (Dashboard) | http://localhost:8080 |
| API REST | http://localhost:3000 |
| API Health Check | http://localhost:3000/api/health |

#### Comandos Uteis

```bash
# Parar todos os servicos
docker compose down

# Reconstruir imagens
docker compose up -d --build

# Verificar logs de um servico especifico
docker compose logs -f api
docker compose logs -f frontend
docker compose logs -f mcp-server

# Limpar dados de atividade
curl -X DELETE http://localhost:3000/api/activity
```

### 2. Docker (Somente MCP Server)

Para usar apenas o servidor MCP com o Claude Desktop:

#### Imagem Pre-construida

```json
{
  "mcpServers": {
    "otrs": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e",
        "OTRS_BASE_URL=https://seu-servidor-otrs/otrs/nph-genericinterface.pl/Webservice/TestInterface",
        "-e",
        "OTRS_USERNAME=seu-usuario",
        "-e",
        "OTRS_PASSWORD=sua-senha",
        "-e",
        "OTRS_VERIFY_SSL=false",
        "-e",
        "OTRS_DEFAULT_QUEUE=Raw",
        "-e",
        "OTRS_DEFAULT_STATE=new",
        "-e",
        "OTRS_DEFAULT_PRIORITY=3 normal",
        "ghcr.io/eduardoantoniojunior/otrs-mcp-server:latest"
      ]
    }
  }
}
```

#### Build Local

```bash
# Clonar e buildar
git clone https://github.com/eduardoantoniojunior/otrs-mcp-server.git
cd otrs-mcp-server
docker build -t otrs-mcp-server .

# Executar
docker run --rm -i \
  -e OTRS_BASE_URL="https://seu-servidor-otrs/otrs/nph-genericinterface.pl/Webservice/TestInterface" \
  -e OTRS_USERNAME="seu-usuario" \
  -e OTRS_PASSWORD="sua-senha" \
  -e OTRS_VERIFY_SSL="false" \
  otrs-mcp-server
```

### 3. Ambiente Local com UV

Para desenvolvimento ou execucao direta sem Docker.

#### Instalar UV

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Configurar o Ambiente

```bash
# Instalar Python 3.12
uv python install 3.12

# Instalar dependencias
uv sync --python 3.12 --extra dev
```

#### Configurar Variaveis de Ambiente

```bash
# Copiar template
cp .env.example .env

# Ou exportar manualmente
export OTRS_BASE_URL="https://seu-servidor-otrs/otrs/nph-genericinterface.pl/Webservice/TestInterface"
export OTRS_USERNAME="seu-usuario"
export OTRS_PASSWORD="sua-senha"
export OTRS_VERIFY_SSL="false"
export OTRS_DEFAULT_QUEUE="Raw"
export OTRS_DEFAULT_STATE="new"
export OTRS_DEFAULT_PRIORITY="3 normal"
export OTRS_DEFAULT_TYPE="Unclassified"
```

#### Executar o MCP Server

```bash
uv run python -m otrs_mcp.main
```

#### Executar a API REST

```bash
uv run uvicorn otrs_mcp.api:app --host 0.0.0.0 --port 3000
```

#### Configurar no Claude Desktop

Edite o arquivo de configuracao do Claude Desktop e adicione:

```json
{
  "mcpServers": {
    "otrs": {
      "command": "uv",
      "args": [
        "--directory",
        "/caminho/completo/para/otrs-mcp-server",
        "run",
        "src/otrs_mcp/main.py"
      ],
      "env": {
        "OTRS_BASE_URL": "https://seu-servidor-otrs/otrs/nph-genericinterface.pl/Webservice/TestInterface",
        "OTRS_USERNAME": "seu-usuario",
        "OTRS_PASSWORD": "sua-senha",
        "OTRS_VERIFY_SSL": "false"
      }
    }
  }
}
```

> Se encontrar o erro `Error: spawn uv ENOENT`, especifique o caminho completo para o `uv` ou defina a variavel `NO_UV=1` na configuracao.

---

## Referencia da API REST

A API REST esta disponivel na porta 3000 apos iniciar o servico.

### Health Check

```
GET /api/health
```

**Resposta:**
```json
{"status": "ok"}
```

### Listar / Buscar Tickets

```
GET /api/tickets
```

**Parametros de Query:**

| Parametro | Tipo | Obrigatorio | Padrao | Descricao |
|---|---|---|---|---|
| `customer_user` | string | Nao | -- | Filtrar por usuario cliente |
| `queue` | string | Nao | -- | Filtrar por fila |
| `state` | string | Nao | -- | Filtrar por estado |
| `priority` | string | Nao | -- | Filtrar por prioridade |
| `title` | string | Nao | -- | Filtrar por titulo |
| `limit` | int | Nao | 50 | Limite de resultados (1-200) |
| `sort_by` | string | Nao | Age | Campo para ordenacao |
| `order_by` | string | Nao | Down | Direcao (Up/Down) |

**Exemplo:**
```bash
curl "http://localhost:3000/api/tickets?queue=Raw&state=new&limit=10"
```

### Obter Detalhes do Ticket

```
GET /api/tickets/{id}
```

**Exemplo:**
```bash
curl http://localhost:3000/api/tickets/123
```

### Criar Ticket

```
POST /api/tickets
```

**Corpo da Requisicao:**

| Campo | Tipo | Obrigatorio | Descricao |
|---|---|---|---|
| `title` | string | Sim | Titulo do ticket |
| `body` | string | Sim | Corpo/artigo do ticket |
| `queue` | string | Nao | Fila (default: Raw) |
| `priority` | string | Nao | Prioridade (default: 3 normal) |
| `state` | string | Nao | Estado (default: new) |
| `customer_user` | string | Nao | Usuario cliente |
| `ticket_type` | string | Nao | Tipo do ticket |

**Exemplo:**
```bash
curl -X POST http://localhost:3000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Problema no sistema",
    "body": "O sistema esta lento",
    "queue": "Raw",
    "priority": "4 high"
  }'
```

### Atualizar Ticket

```
PUT /api/tickets/{id}
```

**Corpo da Requisicao:**

| Campo | Tipo | Descricao |
|---|---|---|
| `title` | string | Novo titulo |
| `queue` | string | Nova fila |
| `priority` | string | Nova prioridade |
| `state` | string | Novo estado |
| `customer_user` | string | Novo usuario cliente |
| `owner` | string | Novo proprietario |

**Exemplo:**
```bash
curl -X PUT http://localhost:3000/api/tickets/123 \
  -H "Content-Type: application/json" \
  -d '{"state": "open", "owner": "agente1"}'
```

### Historico do Ticket

```
GET /api/tickets/{id}/history
```

**Exemplo:**
```bash
curl http://localhost:3000/api/tickets/123/history
```

### Atividade

```
GET  /api/activity          # Listar eventos
GET  /api/activity/summary  # Resumo de metricas
DELETE /api/activity         # Limpar dados
```

**Parametros de Query para `/api/activity`:**

| Parametro | Tipo | Padrao | Descricao |
|---|---|---|---|
| `limit` | int | 50 | Limite de eventos (1-500) |
| `tool` | string | -- | Filtrar por nome da tool |
| `status` | string | -- | Filtrar por status (success/error) |

**Exemplo:**
```bash
curl "http://localhost:3000/api/activity?tool=create_ticket&status=success&limit=20"
curl http://localhost:3000/api/activity/summary
```

### Codigos de Resposta HTTP

| Codigo | Descricao |
|---|---|
| `200` | Requisicao bem-sucedida |
| `201` | Ticket criado com sucesso |
| `401` | Credenciais OTRS invalidas |
| `404` | Ticket nao encontrado |
| `422` | Dados de entrada invalidos (ex: prioridade invalida) |
| `500` | Erro interno do servidor |
| `502` | Erro na API OTRS |
| `503` | Servico OTRS indisponivel |

---

## Referencia das Tools MCP

Estas tools ficam disponiveis para assistentes de IA via o protocolo MCP.

### create_ticket

Cria um novo ticket no OTRS.

**Parametros:**

| Parametro | Tipo | Obrigatorio | Descricao |
|---|---|---|---|
| `title` | string | Sim | Titulo do ticket |
| `body` | string | Sim | Corpo/artigo do ticket |
| `queue` | string | Nao | Fila (default: Raw) |
| `priority` | string | Nao | Prioridade (default: 3 normal) |
| `state` | string | Nao | Estado (default: new) |
| `customer_user` | string | Nao | Usuario cliente |
| `ticket_type` | string | Nao | Tipo do ticket |

**Valores validos para prioridade:** `1 very low`, `2 low`, `3 normal`, `4 high`, `5 very high`

**Valores validos para fila:** `Raw`, `Junk`, `Misc`

**Valores validos para estado:** `new`, `open`, `closed successful`, `closed unsuccessful`, `pending reminder`, `pending auto close`

### get_ticket

Obtem detalhes completos de um ticket, incluindo campos dinamicos e dados estendidos.

**Parametros:**

| Parametro | Tipo | Obrigatorio | Descricao |
|---|---|---|---|
| `ticket_id` | string | Sim | ID do ticket |
| `include_dynamic_fields` | bool | Nao | Incluir campos dinamicos (default: true) |
| `include_extended_data` | bool | Nao | Incluir dados estendidos (default: true) |

### search_tickets

Busca tickets no OTRS com filtros.

**Parametros:**

| Parametro | Tipo | Obrigatorio | Descricao |
|---|---|---|---|
| `customer_user` | string | Nao | Filtrar por usuario cliente |
| `queue` | string | Nao | Filtrar por fila |
| `state` | string | Nao | Filtrar por estado |
| `priority` | string | Nao | Filtrar por prioridade |
| `title` | string | Nao | Filtrar por titulo |
| `limit` | int | Nao | Limite de resultados (default: 50) |
| `sort_by` | string | Nao | Campo de ordenacao (default: Age) |
| `order_by` | string | Nao | Direcao: Up ou Down (default: Down) |

### update_ticket

Atualiza as propriedades de um ticket existente.

**Parametros:**

| Parametro | Tipo | Obrigatorio | Descricao |
|---|---|---|---|
| `ticket_id` | string | Sim | ID do ticket |
| `title` | string | Nao | Novo titulo |
| `queue` | string | Nao | Nova fila |
| `priority` | string | Nao | Nova prioridade |
| `state` | string | Nao | Novo estado |
| `customer_user` | string | Nao | Novo usuario cliente |
| `owner` | string | Nao | Novo proprietario |

### get_ticket_history

Obtem o historico completo de um ticket.

**Parametros:**

| Parametro | Tipo | Obrigatorio | Descricao |
|---|---|---|---|
| `ticket_id` | string | Sim | ID do ticket |

---

## Referencia dos Resources MCP

Resources fornecem acesso direto a dados do OTRS via URIs.

| URI | Descricao |
|---|---|
| `otrs://ticket/{ticket_id}` | Dados completos do ticket em formato JSON |
| `otrs://ticket/{ticket_id}/history` | Historico completo do ticket |
| `otrs://search/tickets` | Lista dos 20 tickets mais recentes |

---

## Variaveis de Ambiente

### Obrigatorias

| Variavel | Descricao |
|---|---|
| `OTRS_BASE_URL` | URL completa do webservice OTRS |
| `OTRS_USERNAME` | Usuario do OTRS |
| `OTRS_PASSWORD` | Senha do OTRS |

### Opcionais

| Variavel | Padrao | Descricao |
|---|---|---|
| `OTRS_VERIFY_SSL` | `false` | Verificar certificados SSL |
| `OTRS_TIMEOUT` | `30` | Timeout HTTP em segundos |
| `OTRS_DEBUG` | `false` | Habilitar logging de debug |
| `OTRS_DEFAULT_QUEUE` | `Raw` | Fila padrao para novos tickets |
| `OTRS_DEFAULT_STATE` | `new` | Estado padrao para novos tickets |
| `OTRS_DEFAULT_PRIORITY` | `3 normal` | Prioridade padrao para novos tickets |
| `OTRS_DEFAULT_TYPE` | `Unclassified` | Tipo padrao para novos tickets |
| `OTRS_WEB_BASE_URL` | (derivado de base_url) | URL da interface web do OTRS |
| `OTRS_CORS_ORIGINS` | `http://localhost:5173,http://localhost:8080` | Origens permitidas para CORS na API |
| `OTRS_ACTIVITY_FILE` | `activity.json` | Caminho do arquivo de log de atividade |
| `OTRS_ACTIVITY_MAX_EVENTS` | `1000` | Maximo de eventos de atividade armazenados |

---

## Desenvolvimento

### Estrutura do Projeto

```
otrs-mcp-server/
├── src/otrs_mcp/           # Pacote Python principal
│   ├── __init__.py         # API publica
│   ├── main.py             # Entry point (MCP server via stdio)
│   ├── config.py           # Configuracao (pydantic-settings)
│   ├── client.py           # Cliente HTTP com retry e sessao
│   ├── tools.py            # Tools MCP (5 tools)
│   ├── resources.py        # Resources MCP (3 resources)
│   ├── api.py              # Backend REST (FastAPI)
│   ├── activity.py         # Sistema de monitoramento de atividade
│   ├── constants.py        # Filas, prioridades e estados validos
│   └── exceptions.py       # Excecoes customizadas
├── frontend/               # Frontend React + TypeScript
├── tests/                  # Testes unitarios e de integracao
├── Dockerfile              # Container do MCP server
├── Dockerfile.api          # Container da API REST
├── docker-compose.yml      # Orquestracao dos servicos
└── pyproject.toml          # Configuracao do projeto (uv/hatch)
```

### Instalacao para Desenvolvimento

```bash
# Clonar o repositorio
git clone https://github.com/eduardoantoniojunior/otrs-mcp-server.git
cd otrs-mcp-server

# Instalar UV (se nao tiver)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Instalar dependencias
uv sync --python 3.12 --extra dev
```

### Executar Testes

```bash
# Testes unitarios
uv run pytest tests/unit/ -v

# Testes com cobertura
uv run pytest tests/unit/ --cov=src/otrs_mcp --cov-report=term-missing

# Testes de integracao (requer OTRS ativo)
export OTRS_BASE_URL="https://seu-servidor/otrs/nph-genericinterface.pl/Webservice/TestInterface"
export OTRS_USERNAME="seu-usuario"
export OTRS_PASSWORD="sua-senha"
uv run pytest tests/integration/ -v -m integration
```

### Formatacao e Qualidade de Codigo

```bash
# Formatacao com black
uv run black src/

# Ordenacao de imports com isort
uv run isort src/

# Type checking com mypy
uv run mypy src/

# Hooks pre-commit
pre-commit install
pre-commit run --all-files
```

### Scripts CLI Disponiveis

Apos instalar o pacote, dois comandos ficam disponiveis:

```bash
# Executar o MCP server
otrs-mcp-server

# Executar a API REST
otrs-mcp-api
```

---

## Solucao de Problemas

### Erros Comuns

1. **Erros de SSL**: Defina `OTRS_VERIFY_SSL=false` para certificados auto-assinados
2. **Redirecionamentos HTTP 301**: Use URLs HTTPS se o servidor OTRS redireciona HTTP para HTTPS
3. **Falhas de autenticacao**: Verifique seu usuario, senha e a configuracao do webservice
4. **Operacoes faltantes**: Verifique se seu webservice OTRS inclui todas as operacoes necessarias

### Modo Debug

Execute o script de diagnostico para problemas de conexao:

```bash
uv run python otrs_mcp_connectivity_test.py
```

Este script testa conexoes HTTP e HTTPS e fornece informacoes detalhadas de erro.

### Exemplo de Configuracao Funcional

```bash
# Variaveis de ambiente
export OTRS_BASE_URL="https://seu-otrs.com/otrs/nph-genericinterface.pl/Webservice/TestInterface"
export OTRS_USERNAME="seu-usuario"
export OTRS_PASSWORD="sua-senha"
export OTRS_VERIFY_SSL="false"
export OTRS_DEFAULT_QUEUE="Raw"
export OTRS_DEFAULT_STATE="new"
export OTRS_DEFAULT_PRIORITY="3 normal"
export OTRS_DEFAULT_TYPE="Unclassified"
```

---

## Licenca

Apache-2.0

---

[mcp]: https://modelcontextprotocol.io
