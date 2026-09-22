# Documentar `HistoryWebURL` nas tools

O client já injeta `HistoryWebURL` em `get_ticket` e `get_ticket_history`
(ver `client.py`):

```python
result["WebURL"] = self._config.get_ticket_web_url(ticket_id)
result["HistoryWebURL"] = self._config.get_ticket_history_web_url(ticket_id)
```

Mas o README, seção "Tools MCP", só menciona `WebURL`. Consumidores lêem
o README e não descobrem o `HistoryWebURL`, então acabam construindo o
link manualmente (ou nem oferecem).

Contexto de uso real: o bou-vigilante responde ao usuário no WhatsApp com
link do ticket depois de criar. Para "mostrar o histórico do ticket 4821"
o link ideal já vem pronto no retorno — só falta o README expor.

## Tasks

- [ ] 1. README, seção "Tools MCP"
  - Coluna "Observações" das linhas `get_ticket` e `get_ticket_history`:
    adicionar "Retorna `WebURL` e `HistoryWebURL` prontos para redirect".

- [ ] 2. README, seção "Como usar o MCP" → "Exemplos de pedidos ao agente"
  - Frase atual: "Toda resposta de ticket inclui `WebURL` (e
    `HistoryWebURL`, quando aplicável)" — trocar por lista concreta de
    quais tools trazem qual link.

- [ ] 3. Docstrings das tools
  - `get_ticket` e `get_ticket_history` no `tools.py`: docstring/description
    da tool passa a listar os campos de link retornados. Isso vai
    direto para a lista de tools que o agente vê no `list_tools`.

- [ ] 4. `search_tickets`
  - Docstring também menciona `WebSearchURL` e `TicketWebURLs`, que já
    são retornados mas idem, não documentados.
