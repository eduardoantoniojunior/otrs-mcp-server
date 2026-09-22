# Escrever artigo/comentário em ticket existente

Hoje o servidor só sabe **criar** ticket com artigo (`create_ticket` monta um
`Article` no `TicketCreate`) ou **atualizar campos** do ticket (`update_ticket`
mexe em `Title`, `Queue`, `Priority`, `State`, `CustomerUser`, `Owner`).
Não existe caminho para adicionar uma nota, resposta ao cliente, ou registro
de auditoria a um ticket já aberto.

Consequência prática no bou-vigilante: a task 15 (fechar o rastro alerta ↔
ticket) hoje é resolvida do lado do Zabbix (`ack_event_zabbix` mete o número
do ticket no evento), mas o **oposto** — anexar o número do evento Zabbix ao
ticket OTRS — só dá para fazer via `WebURL` manual. E responder ao cliente
pelo WhatsApp com o texto aparecendo no ticket é impossível.

## Contexto e decisões

O Ticket Connector do OTRS aceita bloco `Article` dentro de `TicketUpdate`,
igual ao `TicketCreate`. É o mesmo caminho que o `client.create_ticket` já
usa, só que aplicado a um `TicketID` existente.

Decisões:

1. **Tool separada, não parâmetro em `update_ticket`.** `update_ticket` hoje
   passa só campos preenchidos; adicionar um `article_body` opcional infla
   a assinatura e mistura escrita de campos com escrita de conteúdo. Uma
   tool dedicada é mais fácil de instruir o agente ("para responder ao
   cliente, use `add_ticket_article`; para mudar status, use
   `update_ticket`").
2. **Visibilidade explícita.** `IsVisibleForCustomer` decide se o artigo
   aparece para o cliente ou fica interno. Exigir o campo (sem default
   silencioso) evita vazar nota interna como resposta ao cliente.
3. **`ArticleType` derivado.** OTRS aceita valores como `note-internal`,
   `note-external`, `phone`, `email-external`. Deixar o agente escolher
   entre uma lista fechada validada; default `note-internal` quando não
   informado.
4. **Escopo `write`.** Mesmo escopo do `create_ticket` e `update_ticket`.

## Tasks

- [ ] 1. Descobrir o schema aceito pelo webservice
  - `TicketUpdate` com `Ticket` vazio e bloco `Article` completo — confirmar
    se aceita ou se exige pelo menos um campo de ticket.
  - Registrar `ArticleType` válidos na instância (varia entre 4 e 6 valores
    dependendo da configuração do OTRS). Sugestão de mínimo aceito:
    `note-internal`, `note-external`, `email-external`.

- [ ] 2. Client: novo método `add_article`
  - `OTRSClient.add_article(ticket_id, subject, body, article_type,
    is_visible_for_customer, content_type="text/plain; charset=utf8",
    time_unit=1, sender_type=None) -> dict`.
  - Monta payload `{"TicketID": ..., "Article": {...}}` e chama
    `TicketUpdate`.
  - Devolve resposta com `ArticleID` da resposta + `WebURL` do ticket.

- [ ] 3. Tool MCP `add_ticket_article`
  - Escopo `write`.
  - `validate_ticket_id(ticket_id)` antes de tudo.
  - Valida `article_type` contra whitelist em `constants.py`
    (`VALID_ARTICLE_TYPES`).
  - `record_tool_call` grava `tool="add_ticket_article"`, `status`,
    `duration_ms`, `ticket_id`, `params={"article_type": ...,
    "is_visible_for_customer": ...}`. **Não** grava o `body` na atividade
    (dado potencialmente sensível).

- [ ] 4. API REST
  - `POST /api/tickets/{id}/articles` — corpo com `subject`, `body`,
    `article_type`, `is_visible_for_customer`, opcional
    `sender_type`/`time_unit`.
  - Requer `write`.
  - Devolve `ArticleID` + `WebURL`.

- [ ] 5. Painel administrativo (opcional)
  - Botão "Adicionar nota" no `TicketDetail` do frontend, com toggle
    "visível para cliente" e select de tipo.

- [ ] 6. Testes unitários
  - Mock do webservice retornando `ArticleID`; validar whitelist de tipo,
    escopo, validação de `ticket_id`, e que o body **não** aparece em
    `activity.json`.

- [ ] 7. Documentação
  - `README.md`: nova entrada em Tools MCP e API REST.
  - Exemplo em "Exemplos de pedidos ao agente":
    "Responda o ticket 4821 dizendo que o toner foi solicitado, visível
    para o cliente".
  - Avisar bou-vigilante: dá para reescrever a task 15 usando esta tool
    (anexar o `event_id` do Zabbix como nota interna no ticket recém-criado).
