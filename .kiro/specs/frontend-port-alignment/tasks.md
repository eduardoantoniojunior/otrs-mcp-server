# Alinhar porta do frontend entre Compose e Nginx

Limitação nº 1 documentada no README: o Compose publica
`127.0.0.1:8081:80`, mas `nginx/mcp.conf` faz `proxy_pass 127.0.0.1:8080`.
Resultado: sem ajuste manual, `/otrs/` responde 502 na primeira instalação
seguindo o README ao pé da letra.

## Contexto e decisões

Estado atual:

- `docker-compose.yml` → `frontend.ports: - "127.0.0.1:8081:80"`.
- `nginx/mcp.conf` → `proxy_pass http://127.0.0.1:8080;`.

Decisões:

1. **Padronizar em 8081.** Foi a porta escolhida no Compose (a que os
   deploys existentes já usam). Mexer no Compose implicaria mexer em
   máquinas de produção; mexer no vhost é local à instalação nova.
2. **Comentário no vhost.** Deixar explícito por que é 8081, para não
   voltar a divergir num futuro rebuild do `mcp.conf`.

## Tasks

- [ ] 1. Ajustar `nginx/mcp.conf`
  - Trocar `proxy_pass http://127.0.0.1:8080;` por
    `proxy_pass http://127.0.0.1:8081;` no `location /otrs/`.
  - Adicionar comentário: `# Compose publica frontend em 127.0.0.1:8081`.

- [ ] 2. Verificar outros pontos onde a porta aparece
  - `deploy/*.sh`, `docker-compose.yml`, README, exemplos de curl.
  - Se algum script recarrega o Nginx a partir de template, atualizar
    lá também.

- [ ] 3. Remover o item 1 de "Limitações conhecidas" no README

- [ ] 4. Teste manual pós-mudança
  - `sudo nginx -t && sudo systemctl reload nginx`
  - `curl -I https://seu-dominio/otrs/` deve responder 200 (ou 301 → SPA).
