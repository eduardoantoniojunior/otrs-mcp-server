# Reduzir custo do `list_customer_users`

Estado atual (`OTRSClient.search_customer_users`):

1. `TicketSearch(limit=200, Result="ARRAY")` — devolve só a lista de
   `TicketID`.
2. Para cada `TicketID`, um `TicketGet` individual só para extrair
   `CustomerUserID`, `CustomerName`, `CustomerID`.

Com `limit=200`, são **201 chamadas** ao OTRS. Numa instância grande, isso
gasta minutos e satura a sessão do webservice.

## Contexto e decisões

O Ticket Connector aceita `Result="HASH"` no `TicketSearch` (retorna cada
ticket com seus campos básicos já preenchidos, incluindo `CustomerUserID`
e `CustomerID`, numa única resposta). Quando o webservice tem
`CustomerUserSearch` habilitado, dá para pular tickets e listar customers
diretamente — mais rápido ainda, mas depende de configuração no OTRS.

Decisões:

1. **`Result="HASH"` como caminho padrão.** Uma chamada substitui as 201
   atuais. Não depende de operação extra no webservice.
2. **`CustomerUserSearch` como caminho opcional.** Se o webservice
   expuser a operação, usá-la; senão, cair no HASH. Detecção por
   configuração explícita (env `OTRS_HAS_CUSTOMER_USER_SEARCH=true`) —
   testar em runtime é frágil e cache-friendly.
3. **Manter o schema de saída.** `{"CustomerUsers": [{"Login", "Name",
   "CustomerID"}, ...]}`. Mudança é interna, sem quebrar clientes.

## Tasks

- [ ] 1. Confirmar retorno do `TicketSearch` com `Result="HASH"`
  - Rodar contra a instância de teste, registrar as chaves presentes por
    ticket (`CustomerUserID`, `CustomerID`, `CustomerName` — a última
    pode estar ausente dependendo do OTRS).
  - Se `CustomerName` não vier, avaliar cair em `CustomerUserID` como
    display name (não é ideal, mas 1 chamada > N+1).

- [ ] 2. Reescrever `search_customer_users`
  - Uma única chamada `TicketSearch(Result="HASH", Limit=limit,
    SortBy="Age", OrderBy="Down")`.
  - Iterar o dict retornado, deduplicar por `CustomerUserID`, montar a
    lista final. Sem `TicketGet` no meio.

- [ ] 3. Suporte opcional a `CustomerUserSearch`
  - Env `OTRS_HAS_CUSTOMER_USER_SEARCH=true` liga o caminho novo.
  - Novo método `client.search_customer_users_native(search: str | None,
    limit: int)` que chama a operação direto.
  - Documentar no README como habilitar no webservice do OTRS.

- [ ] 4. Testes unitários
  - Mock do `TicketSearch` com HASH, validar deduplicação e o schema
    de saída.
  - Se implementar (3), mock do `CustomerUserSearch` também.

- [ ] 5. Documentar no README
  - Tabela de tools: nota que `list_customer_users` deriva de tickets
    recentes e recomenda habilitar `CustomerUserSearch` para bases com
    muitos clientes.
