# Robustecer `_discover_default_type`

`OTRSClient._discover_default_type` faz `TicketSearch(limit=1)` +
`TicketGet` para extrair o campo `Type` de um ticket qualquer e cacheia
em `self._discovered_type`. Problema:

- Se a **primeira** chamada acontecer numa instância sem tickets ainda
  (deploy novo, base recém-criada), `_discovered_type` fica `""` para
  sempre no ciclo de vida do processo.
- A partir daí, todo `create_ticket` sem `ticket_type` sai sem `Type` no
  payload — e se a fila exigir Type (comum em instalações padrão do OTRS),
  a criação falha silenciosamente com erro do webservice.

## Contexto e decisões

Decisões:

1. **Não cachear resultado vazio.** Se a descoberta falhou, permitir nova
   tentativa na próxima criação de ticket. O custo (`TicketSearch +
   TicketGet`) só volta a acontecer enquanto a base estiver vazia.
2. **`OTRS_DEFAULT_TYPE` como caminho preferencial.** Documentar no README
   como recomendação explícita para instâncias novas ou onde o Type deve
   ser determinístico (o comportamento atual é "pega o Type do primeiro
   ticket que encontrar", o que é imprevisível).
3. **Cache com TTL curto (opcional).** Se a instância adicionar/remover
   Types no OTRS, o cache atual nunca refletiria. TTL de 1h reconcilia
   sem custo perceptível.

## Tasks

- [ ] 1. Não cachear vazio
  ```python
  if discovered:
      self._discovered_type = discovered
  # se vazio, deixa None para retry na próxima chamada
  ```

- [ ] 2. Log de warning no primeiro miss
  - Já existe (`"Nenhum ticket encontrado para descobrir o Type padrao"`).
    Elevar de `warning` para `error` e sugerir configurar
    `OTRS_DEFAULT_TYPE`.

- [ ] 3. Cache com TTL (opcional, se justificado pelo uso)
  - `self._discovered_type_at: float | None`.
  - Invalidar após 3600 s. Trivial, mas só vale se algum consumidor
    reclamar de Type velho.

- [ ] 4. README
  - Seção "OTRS — opcionais": destacar `OTRS_DEFAULT_TYPE` como
    recomendação para instalações novas.
  - Seção "Solução de problemas": entrada nova — "Criação de ticket
    falha em instância sem tickets pré-existentes → definir
    `OTRS_DEFAULT_TYPE`".

- [ ] 5. Teste unitário
  - Mock do `TicketSearch` sem tickets, validar que uma segunda chamada
    a `create_ticket` **tenta descobrir de novo** (não usa cache vazio).
