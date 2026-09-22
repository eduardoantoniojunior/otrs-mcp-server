# Rate limit e usage_count coerentes no transporte MCP

Duas limitações listadas no próprio README (`Limitações conhecidas` itens 2 e
3):

- Rate limit é calculado a partir de `api_usage`, mas as tools MCP registram
  atividade só em `activity.json`. Uma API key usada 100% via MCP nunca
  aciona o rate limit — a proteção existe só para a API REST.
- Ao mesmo tempo, `usage_count` de uma key sobe uma vez a cada requisição
  HTTP do transporte streamable-http. Uma única sessão MCP faz várias
  requisições (initialize, list_tools, call_tool, etc.), então o contador
  infla e não reflete o uso real de tools.

Resultado: os dois indicadores mais visíveis do painel — rate limit acionado
e "chamadas por key" — não fazem sentido para consumidores MCP.

## Contexto e decisões

Estado atual (verificado em `src/otrs_mcp/`):

- `mcp_auth.ApiKeyVerifier` valida a key em cada request HTTP do
  streamable-http, e o middleware `RequireAuthMiddleware` incrementa
  `usage_count` (via `database.record_key_usage` ou equivalente) por
  request — não por tool executada.
- `tools.py` chama `record_tool_call` no fim de cada tool, que grava só em
  `activity.json` via `activity.record_tool_call`.
- `auth.check_rate_limit` faz `SELECT COUNT(*) FROM api_usage WHERE
  api_key_id = ? AND created_at > now - 60s`. `api_usage` só é populada
  pelo `record_api_call` chamado nas rotas REST (`otrs_mcp/api.py` e
  `routes/admin.py`).

Decisões:

1. **`api_usage` vira a fonte única de verdade para rate limit e métricas.**
   `activity.json` continua existindo como log rápido/textual, mas o
   contador oficial passa a ser SQL.
2. **Uma tool executada = uma linha em `api_usage`.** Não uma linha por
   request HTTP. A entrada do incremento sai do middleware e passa a ser
   feita dentro das tools, junto com `record_tool_call`.
3. **`usage_count` deriva de `api_usage`.** Elimina o contador redundante
   na tabela `api_keys` (ou passa a ser reconciliado periodicamente); o
   painel passa a mostrar `COUNT(*) FROM api_usage WHERE api_key_id = ?`.

## Tasks

- [ ] 1. Mapear pontos que gravam contador hoje
  - `RequireAuthMiddleware` / `ApiKeyVerifier`: onde exatamente
    `usage_count` é incrementado.
  - Todas as chamadas a `record_api_call` na API REST.
  - Todas as chamadas a `record_tool_call` em `tools.py`/`resources.py`.
  - Documentar o inventário como comentário na PR ou aqui, para não
    esquecer nenhum caminho.

- [ ] 2. Consolidar registro em um helper
  - Novo `database.record_usage(api_key_id, tool_or_endpoint, ticket_id,
    duration_ms, status, error)` que **sempre** insere em `api_usage`.
  - `record_tool_call` do `activity.py` continua para o `activity.json`,
    mas agora chama `record_usage` também (quando `api_key_id` está no
    contexto — no `stdio` não estará; documentar).

- [ ] 3. Remover o incremento por request HTTP no MCP
  - `RequireAuthMiddleware` deixa de gravar em `api_usage` /
    `usage_count`. A validação de existência da key permanece.
  - `check_rate_limit` continua rodando por request HTTP (na validação da
    key), mas a contagem passa a refletir tools executadas.
  - Trade-off: uma tool cara conta 1, um flood de `initialize` conta 0.
    Aceitável — o rate limit é sobre custo de negócio, não sobre HTTP.

- [ ] 4. `usage_count` passa a ser derivado
  - Opção A: view materializada / trigger que mantém
    `api_keys.usage_count` sincronizado com `COUNT(*) FROM api_usage`.
  - Opção B: remover a coluna e o painel calcular ao vivo. Mais simples,
    mais lento em telas com muitas keys.
  - Decidir na task; a opção A tem menos impacto no frontend.

- [ ] 5. Backfill (opcional)
  - Script para inspecionar `activity.json` histórico e alimentar
    `api_usage` retroativamente. Só vale se o painel precisar de série
    histórica correta.

- [ ] 6. Testes
  - `tests/unit/test_rate_limit_mcp.py`: mock de tool call, verificar que
    N chamadas sequenciais em <60s são cortadas por `check_rate_limit`.
  - `tests/unit/test_usage_count.py`: uma sessão MCP com N tool calls =
    N linhas em `api_usage`, independente de quantos requests HTTP
    aconteceram por baixo.

- [ ] 7. Atualizar README
  - Remover os itens 2 e 3 de "Limitações conhecidas".
  - Seção Segurança: rate limit passa a valer para todos os transportes.
