#!/usr/bin/env bash
# =============================================================================
# OTRS MCP Server — Health Check Externo
# =============================================================================
# Verifica se os 3 servicos estao respondendo e envia alerta se algum cair.
#
# Uso:
#   ./deploy/healthcheck.sh                    # Verificacao manual
#   crontab: */5 * * * * /opt/otrs-mcp-server/deploy/healthcheck.sh
#
# Alertas (opcional):
#   Configure HEALTHCHECK_WEBHOOK_URL no .env para receber notificacoes
#   via webhook (Slack, Discord, Teams, etc).
# =============================================================================

set -euo pipefail

API_URL="http://127.0.0.1:3000/api/health"
MCP_URL="http://127.0.0.1:8001"
FRONTEND_URL="http://127.0.0.1:8080"
WEBHOOK_URL="${HEALTHCHECK_WEBHOOK_URL:-}"
LOG_FILE="/var/log/otrs-mcp-health.log"
ALERT_FILE="/tmp/otrs-mcp-alert-sent"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" 2>/dev/null || echo "$1"
}

send_alert() {
    local message="$1"
    log "ALERTA: $message"

    # Enviar webhook se configurado
    if [ -n "$WEBHOOK_URL" ]; then
        curl -sf -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"[OTRS MCP] $message\"}" \
            > /dev/null 2>&1 || true
    fi
}

send_recovery() {
    local message="$1"
    log "RECUPERADO: $message"

    if [ -n "$WEBHOOK_URL" ]; then
        curl -sf -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"[OTRS MCP] RECUPERADO: $message\"}" \
            > /dev/null 2>&1 || true
    fi
}

FAILED=0
DETAILS=""

# Verificar API
if curl -sf --max-time 10 "$API_URL" > /dev/null 2>&1; then
    DETAILS="${DETAILS}API: OK\n"
else
    DETAILS="${DETAILS}API: FALHA\n"
    FAILED=$((FAILED + 1))
fi

# Verificar MCP Server (testa conexao TCP na porta)
if python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('127.0.0.1', 8001)); s.close()" 2>/dev/null; then
    DETAILS="${DETAILS}MCP: OK\n"
else
    DETAILS="${DETAILS}MCP: FALHA\n"
    FAILED=$((FAILED + 1))
fi

# Verificar Frontend
if curl -sf --max-time 10 "$FRONTEND_URL" > /dev/null 2>&1; then
    DETAILS="${DETAILS}Frontend: OK\n"
else
    DETAILS="${DETAILS}Frontend: FALHA\n"
    FAILED=$((FAILED + 1))
fi

# Resultado
if [ $FAILED -gt 0 ]; then
    # Enviar alerta apenas uma vez (evitar spam a cada 5min)
    if [ ! -f "$ALERT_FILE" ]; then
        send_alert "$FAILED servico(s) indisponivel(is). $(echo -e "$DETAILS" | tr '\n' ' ')"
        touch "$ALERT_FILE"
    fi
    log "CHECK FALHOU: $FAILED servico(s) com problema"
    exit 1
else
    # Se estava em alerta, enviar recuperacao
    if [ -f "$ALERT_FILE" ]; then
        send_recovery "Todos os servicos estao online novamente."
        rm -f "$ALERT_FILE"
    fi
    log "CHECK OK: Todos os servicos respondendo"
    exit 0
fi
