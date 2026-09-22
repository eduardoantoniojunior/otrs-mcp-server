# Expor corpo/artigos dos tickets no MCP

Hoje o `get_ticket` só devolve metadados. Agentes IA que consomem o servidor
(ex.: bou-vigilante) não conseguem responder "o que o cliente disse", "resume
a conversa" ou "que resposta o atendente deu"; só têm `WebURL` para mandar o
usuário abrir no navegador. O bou-vigilante teve que adicionar "REGRA DE
HONESTIDADE" no SYSTEM_PROMPT para conter alucinação — ver
`bou-vigilante/.kiro/specs/otrs-ticket-whatsapp/tasks.md` tasks **19d** e
**19e**.

## Contexto e decisões

Estado atual (verificado em `src/otrs_mcp/client.py`):

- `get_ticket` chama `TicketGet` com `DynamicFields`/`Extended`; **não** passa
  `AllArticles` nem `Articles`, então o Ticket Connector devolve só metadados.
- `get_ticket_history` chama `TicketHistoryGet`, que traz eventos (mudança de
  estado, atribuição, `ArticleID`, timestamps) — sem os corpos.
- O Ticket Connector do OTRS já expõe artigos via `TicketGet` com `AllArticles=1`
  (retorna campos `Article`/`Articles` no ticket) ou via operação `ArticleGet`
  quando ela está exposta no webservice.

Decisões:

1. **Adicionar dois pontos de acesso, não um só.** `include_articles: bool` no
   `get_ticket` é a mudança mínima (o SDK MCP e todos os clientes existentes
   continuam funcionando). Uma tool nova `get_ticket_articles` é melhor para
   instruir o agente ("quando quiser o conteúdo dos artigos, use esta tool")
   e permite paginação/filtros independentes sem inflar `get_ticket`.
2. **Default `False`.** Trazer todos os artigos triplica ou mais o payload de
   um `get_ticket`; a maioria dos consumos hoje é só de metadados. Manter o
   comportamento atual como default e ligar por opt-in.
3. **Filtrar campos sensíveis por padrão.** Artigo bruto do OTRS traz `From`
   (email), `To`, `Cc`, `MimeType`, `ContentType`. Devolver tudo, sem
   sanitização, faz o agente vazar PII no chat. Documentar quais campos são
   incluídos e considerar um whitelist de saída.
4. **Compatibilidade com `TicketConnector` sem `ArticleGet`.** Nem toda
   instância expõe `ArticleGet` como operação separada. Usar `TicketGet` com
   `AllArticles=1` é o caminho universal.

## Tasks

- [ ] 1. Confirmar suporte no webservice em uso
  - Rodar contra `zabbix.mcp.beonup.com.br/otrs/mcp` uma chamada `TicketGet`
    com `AllArticles=1` e registrar o schema real da resposta
    (campo `Article` vs `Articles`, tipo lista vs dict, chaves presentes).
  - Se `ArticleGet` estiver exposto, registrar também o schema — vira o
    caminho preferencial para `get_ticket_articles` com paginação.

- [x] 2. Client: adicionar suporte a artigos no `TicketGet`
  - `OTRSClient.get_ticket(ticket_id, include_dynamic_fields=True,
    include_extended_data=True, include_articles=False, article_limit=None,
    article_order="desc")`.
  - Passar `AllArticles=1` no payload quando `include_articles=True`; incluir
    também `ArticleSenderType`/`ArticleOrder` se o webservice aceitar.
  - Normalizar `Article`/`Articles` para uma lista consistente antes de
    devolver, independente da forma que o OTRS retorna.

- [x] 3. Sanitização de saída
  - Definir whitelist de campos por artigo: `ArticleID`, `Subject`, `Body`,
    `SenderType`, `ArticleType`, `IsVisibleForCustomer`, `CreateTime`,
    `From`, `To`, `ContentType`. Descartar cabeçalhos completos, anexos e
    corpos raw. Documentar no docstring.
  - `record_tool_call` já descarta campos `password`; garantir que corpos
    de artigo **não** entrem em `params` gravados na atividade.

- [x] 4. Tool MCP `get_ticket` com `include_articles`
  - Novo parâmetro opcional, default `False`.
  - Descrição da tool deixando explícito: "quando `include_articles=True`,
    o retorno inclui a lista de artigos com corpo".

- [x] 5. Tool MCP nova `get_ticket_articles`
  - Assinatura: `get_ticket_articles(ticket_id, limit: int = 20,
    order: str = "desc", sender_type: str | None = None)`.
  - Escopo `read`.
  - Internamente reusa `client.get_ticket(..., include_articles=True)` e
    aplica `limit`/`order`/`sender_type` em memória (ou repassa para o
    webservice se `ArticleGet` estiver disponível — decidir na task 1).
  - Retorno: `{"TicketID": ..., "Articles": [...], "TotalCount": N}`.

- [x] 6. Resource MCP `otrs://ticket/{ticket_id}/articles`
  - Espelha `get_ticket_articles(ticket_id, limit=20, order="desc")`.
  - Facilita instruir agentes que consomem por resource.

- [x] 7. Atualizar API REST
  - `GET /api/tickets/{id}?include_articles=1` — query param.
  - `GET /api/tickets/{id}/articles` — novo endpoint.
  - Ambos exigem escopo `read` (`require_permission("read")`).

- [x] 8. Testes unitários
  - Feito, mas em outros arquivos e mais compactos:
    `tests/unit/test_client.py::TestOTRSClientGetTicketWithArticles`
    (11 testes cobrindo AllArticles flag, normalização em 4 formatos,
    whitelist, order asc/desc, limit, sender_type filter).
    `tests/unit/test_client.py::TestOTRSClientGetTicketArticles` (1 teste
    de shape do wrapper).
    `tests/unit/test_tools.py::TestGetTicketArticles` (4 testes) +
    `TestGetTicket::test_get_ticket_with_articles` + `_invalid_article_order`.
    `tests/unit/test_resources.py::TestTicketArticlesResource` (2 testes).
    `tests/unit/test_activity.py` (novo, 4 testes do blocklist).
    Total: 22 testes novos, 69 verdes no total.
  - Contrato REST dos dois endpoints ainda sem cobertura direta — os
    handlers só encaminham para o client já testado; se justificar, adicionar
    depois com `httpx.AsyncClient` sobre a app FastAPI.

- [x] 9. Documentação
  - `README.md`: seções Tools MCP, Resources MCP, API REST, "Exemplos de
    pedidos ao agente" e "Exemplos com cURL" atualizadas. Nota sobre
    whitelist de campos de artigo adicionada.
  - Seção "Limitações conhecidas" não tinha parágrafo específico sobre
    corpo dos tickets (era só documentado no bou-vigilante); a nova seção
    "Tools MCP" agora marca `get_ticket_history` como sem corpo e aponta
    para `get_ticket_articles`.
  - PENDENTE (ação no bou-vigilante, fora deste repo): remover a REGRA DE
    HONESTIDADE do `SYSTEM_PROMPT` e reescrever as docstrings de
    `consultar_ticket_otrs` / `historico_ticket_otrs` (task 19e deles) —
    apontar para `get_ticket(..., include_articles=True)` ou
    `get_ticket_articles(...)`.
