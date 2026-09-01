#!/usr/bin/env bash
# =============================================================================
# OTRS MCP Server — Script de Deploy
# =============================================================================
# Uso:
#   ./deploy/deploy.sh          # Build e restart
#   ./deploy/deploy.sh --pull   # Git pull + build + restart
#
# O que faz:
#   1. (Opcional) Git pull da branch atual
#   2. Build das imagens Docker
#   3. Restart dos containers (um por vez para minimizar downtime)
#   4. Healthcheck para garantir que subiu
#   5. Limpa imagens Docker orfas
# =============================================================================

set -euo pipefail

APP_DIR="/opt/otrs-mcp-server"
COMPOSE="docker compose"
HEALTH_URL="http://127.0.0.1:3000/api/health"
MAX_WAIT=60

cd "$APP_DIR"

echo "=== OTRS MCP Server Deploy ==="
echo "Diretorio: $APP_DIR"
echo "Data: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Git pull (opcional)
if [[ "${1:-}" == "--pull" ]]; then
    echo "[1/5] Git pull..."
    git pull --ff-only
    echo ""
fi

# Backup do banco antes de atualizar
if [ -f deploy/backup.sh ]; then
    echo "[2/5] Backup do banco..."
    bash deploy/backup.sh
    echo ""
else
    echo "[2/5] Backup (script nao encontrado, pulando)"
    echo ""
fi

# Build
echo "[3/5] Build das imagens..."
$COMPOSE build --parallel
echo ""

# Restart (rolling: frontend primeiro, depois api, depois mcp)
echo "[4/5] Restart dos containers..."
$COMPOSE up -d --remove-orphans
echo ""

# Healthcheck
echo "[5/5] Verificando health..."
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        echo "  API respondendo OK"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo "  Aguardando API... (${WAITED}s)"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "  ERRO: API nao respondeu em ${MAX_WAIT}s"
    echo "  Verificar logs: docker compose logs -f api"
    exit 1
fi

# Status
echo ""
$COMPOSE ps
echo ""

# Limpar imagens orfas
echo "Limpando imagens orfas..."
docker image prune -f --filter "until=24h" 2>/dev/null || true

echo ""
echo "=== Deploy finalizado com sucesso ==="
echo "Acesso: https://seu-dominio"
