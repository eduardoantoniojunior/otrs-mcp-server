# Suportar dynamic fields em `update_ticket`

`OTRSClient.update_ticket` hoje aceita só `Title`, `Queue`, `Priority`,
`State`, `CustomerUser`, `Owner`. Não aceita `DynamicField`, embora o
Ticket Connector do OTRS aceite o bloco no mesmo `TicketUpdate`.

Impacto real (bou-vigilante):

- Task 15 do bou-vigilante fecha o rastro alerta↔ticket **do lado do
  Zabbix** (`ack_event_zabbix` mete o número do ticket como comentário
  no evento). O caminho inverso — anexar `ZabbixEventID` como dynamic
  field no ticket OTRS — seria mais limpo (indexável, filtrável no
  painel OTRS), mas hoje não dá via MCP.

## Contexto e decisões

O Ticket Connector aceita:

```json
{
  "TicketID": "4821",
  "Ticket": {"State": "open"},
  "DynamicField": [
    {"Name": "ZabbixEventID", "Value": "12345"}
  ]
}
```

O bloco `DynamicField` pode ser lista de `{Name, Value}` ou dict único.
Preferir lista (o formato universalmente aceito).

Decisões:

1. **Aceitar `dict[str, Any]` na tool.** Converter internamente para
   `[{"Name": k, "Value": v}, ...]`. Mais amigável para o agente do que
   pedir a lista completa.
2. **Validação leve.** Sem lookup no `SysConfig` do OTRS (custo alto);
   confia no webservice para reportar dynamic fields inexistentes. Log
   detalhado na resposta de erro.
3. **Também em `create_ticket`.** Para simetria; adiciona `DynamicField`
   ao payload de `TicketCreate`. Fora do escopo mínimo, mas trivial no
   mesmo PR.

## Tasks

- [ ] 1. Client: adicionar `dynamic_fields` em `update_ticket`
  ```python
  async def update_ticket(
      self, ticket_id, ..., dynamic_fields: dict[str, Any] | None = None
  ):
      ...
      payload = {"TicketID": ticket_id, "Ticket": updates}
      if dynamic_fields:
          payload["DynamicField"] = [
              {"Name": k, "Value": v} for k, v in dynamic_fields.items()
          ]
      return await self.request("TicketUpdate", payload)
  ```

- [ ] 2. Client: mesma coisa em `create_ticket`
  - `dynamic_fields: dict[str, Any] | None = None`, injetado no payload
    do `TicketCreate`.

- [ ] 3. Tool MCP `update_ticket` — novo parâmetro
  - `dynamic_fields: dict[str, str] | None = None`.
  - Docstring com exemplo: `{"ZabbixEventID": "12345"}`.

- [ ] 4. Tool MCP `create_ticket` — novo parâmetro
  - Idem, opcional.

- [ ] 5. API REST
  - `POST /api/tickets` e `PUT /api/tickets/{id}` aceitam campo
    `dynamic_fields` no body.
  - Documentado no README.

- [ ] 6. Testes unitários
  - Mock validando payload enviado ao OTRS quando `dynamic_fields` é
    passado; e que o campo não aparece no payload quando é None.

- [ ] 7. Comunicar bou-vigilante
  - Reescrever a task 15 do lado deles: em vez de escrever só no evento
    Zabbix, também injetar `ZabbixEventID` como dynamic field no
    `create_ticket`. Dá filtro no painel OTRS + rastreabilidade
    bidirecional.
