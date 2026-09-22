# Semântica de `customer_user` em `create_ticket`

O schema MCP marca só `title` e `body` como obrigatórios. Na prática, o
Ticket Connector do OTRS historicamente exige `CustomerUser` para criar
ticket. Hoje o `client.create_ticket` disfarça isso caindo em
`self._config.username` como fallback silencioso:

```python
"CustomerUser": customer_user or self._config.username,
```

Ou seja, todo ticket criado sem `customer_user` fica com o **usuário do
webservice** como cliente. Isso funciona mas:

- Distorce relatórios do OTRS (todos os tickets aparecem vindos do mesmo
  cliente sintético).
- O bou-vigilante (task 1.2 do lado deles, ainda aberta) fez um workaround
  na task 17 — resolver `customer_user` por email do usuário Zabbix +
  `OTRS_DEFAULT_CUSTOMER` — sem saber se o campo era ou não obrigatório
  no servidor.
- Não há env `OTRS_DEFAULT_CUSTOMER`; o único jeito de mudar o fallback
  é trocando o `OTRS_USERNAME`, que também é a credencial do webservice.

## Contexto e decisões

Decisões:

1. **Testar antes de mudar comportamento.** Rodar
   `python test_otrs_mcp.py --create` sem `customer_user` numa instância
   real e registrar o resultado. Se o Ticket Connector aceitar, o
   fallback atual é aceitável; se rejeitar, o schema MCP precisa marcar
   o campo como obrigatório.
2. **Introduzir `OTRS_DEFAULT_CUSTOMER` como env explícita.** Sem tocar
   em `OTRS_USERNAME`. Ordem de precedência:
   `customer_user` do argumento > `OTRS_DEFAULT_CUSTOMER` > `OTRS_USERNAME`.
3. **Log warning no fallback.** Se `customer_user` não veio e caiu em
   `OTRS_USERNAME`, logar warning para o operador perceber a distorção
   de relatório.
4. **Documentação explícita.** README precisa dizer o que acontece quando
   `customer_user` é omitido, e recomendar `OTRS_DEFAULT_CUSTOMER` para
   agentes que criam tickets em massa.

## Tasks

- [ ] 1. Executar teste real
  - `python test_otrs_mcp.py --create` sem `customer_user` na fila de
    teste; registrar aqui o resultado (aceita/rejeita/aceita com quais
    defaults do OTRS).
  - Se rejeitar, capturar a mensagem de erro para documentar.

- [ ] 2. Config: adicionar `OTRS_DEFAULT_CUSTOMER`
  - `OTRSConfig.default_customer: str | None = None` em `config.py`.
  - Env var `OTRS_DEFAULT_CUSTOMER`, opcional.
  - README: linha nova na tabela "OTRS — opcionais".

- [ ] 3. Client: novo fallback com log
  ```python
  customer = (
      customer_user
      or self._config.default_customer
      or self._config.username
  )
  if not customer_user and not self._config.default_customer:
      logger.warning(
          "create_ticket sem customer_user; usando OTRS_USERNAME (%s) "
          "como cliente. Defina OTRS_DEFAULT_CUSTOMER para evitar.",
          self._config.username,
      )
  ```

- [ ] 4. Schema da tool
  - Se a task 1 provar que o webservice exige `CustomerUser`, atualizar
    o docstring do `create_ticket` para deixar claro; a assinatura
    continua `str | None` porque o servidor aplica default por env.
  - Description da tool: "Se `customer_user` não for informado, usa
    `OTRS_DEFAULT_CUSTOMER` ou, na falta, `OTRS_USERNAME`".

- [ ] 5. Comunicar bou-vigilante
  - Task 17 do lado deles já resolve por email do usuário Zabbix; a
    novidade daqui é a env `OTRS_DEFAULT_CUSTOMER`, que substitui o
    "cair em OTRS_USERNAME" atual e permite separar a credencial do
    webservice do cliente sintético. Sugerir eles apontarem
    `OTRS_DEFAULT_CUSTOMER` para um customer "sistema-zabbix" dedicado.

- [ ] 6. Testes unitários
  - Ordem de precedência: argumento > env > username.
  - Warning só dispara quando cai em username.
