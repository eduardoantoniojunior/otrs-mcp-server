# OTRS MCP Server - Guia do Projeto

## Visão Geral

Servidor MCP (Model Context Protocol) para integração com o OTRS (sistema de tickets). Permite que LLMs criem, consultem, busquem e atualizem tickets no OTRS.

## Estrutura do Projeto

```
otrs-mcp-server/
├── src/otrs_mcp/
│   ├── main.py          # Entry point
│   └── server.py        # Core do servidor MCP (tools e resources)
├── tests/               # Testes de integração
├── Dockerfile           # Container multi-stage
├── pyproject.toml       # Config do projeto (uv/hatch)
└── opencode.json        # Config do opencode
```

## Comandos Úteis

```bash
# Instalar dependências
uv sync

# Rodar o servidor
uv run python -m otrs_mcp.main

# Rodar testes
uv run pytest tests/

# Formatação
uv run black src/
uv run isort src/

# Type check
uv run mypy src/
```

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `OTRS_BASE_URL` | Sim | URL base do OTRS (ex: https://instance/otrs/) |
| `OTRS_USERNAME` | Sim | Usuário do OTRS |
| `OTRS_PASSWORD` | Sim | Senha do OTRS |
| `OTRS_DEBUG` | Não | Habilitar debug (true/false) |
| `OTRS_TIMEOUT` | Não | Timeout HTTP em segundos (default: 30) |

## Convenções de Código

- Python 3.12+ (não 3.14)
- Type hints obrigatórios
- Docstrings em português
- Formatação com black (88 chars)
- Imports ordenados com isort

## Funcionalidades Implementadas

### Tools MCP
- `create_ticket` - Criar ticket
- `get_ticket` - Obter detalhes do ticket
- `search_tickets` - Buscar tickets
- `update_ticket` - Atualizar ticket
- `get_ticket_history` - Histórico do ticket

### Resources MCP
- `otrs://ticket/{ticket_id}` - Dados do ticket
- `otrs://ticket/{ticket_id}/history` - Histórico
- `otrs://search/tickets` - Tickets recentes

## Prioridades de Melhoria

1. ~~**CRÍTICO:** Remover credenciais hardcoded~~ ✅ Fase 1 concluída
2. **ALTO:** Modularizar server.py
3. **ALTO:** Adicionar testes unitários
4. **MÉDIO:** Docker compose
5. **MÉDIO:** Frontend web
