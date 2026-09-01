#!/usr/bin/env bash
# =============================================================================
# OTRS MCP Server — Backup do SQLite
# =============================================================================
# Uso:
#   ./deploy/backup.sh              # Backup manual
#   crontab: 0 3 * * * /opt/otrs-mcp-server/deploy/backup.sh
#
# Mantém os últimos 7 backups. Usa sqlite3 .backup para consistência
# (safe mesmo com escritas concorrentes graças ao WAL mode).
# =============================================================================

set -euo pipefail

APP_DIR="/opt/otrs-mcp-server"
BACKUP_DIR="$APP_DIR/backups"
DB_CONTAINER="otrs-mcp-server-api-1"
DB_PATH="/data/otrs-mcp.db"
KEEP_DAYS=7
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/otrs-mcp_${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

echo "[Backup] Iniciando backup do SQLite..."
echo "[Backup] Container: $DB_CONTAINER"
echo "[Backup] Destino: $BACKUP_FILE"

# Usar sqlite3 .backup dentro do container (copia consistente)
docker exec "$DB_CONTAINER" python -c "
import sqlite3, shutil
src = sqlite3.connect('$DB_PATH')
dst = sqlite3.connect('/data/backup_temp.db')
src.backup(dst)
dst.close()
src.close()
" 2>/dev/null

# Copiar do container para o host
docker cp "$DB_CONTAINER:/data/backup_temp.db" "$BACKUP_FILE"

# Limpar temp do container
docker exec "$DB_CONTAINER" rm -f /data/backup_temp.db 2>/dev/null || true

# Comprimir
gzip "$BACKUP_FILE"
FINAL_FILE="${BACKUP_FILE}.gz"

echo "[Backup] Arquivo: $FINAL_FILE ($(du -h "$FINAL_FILE" | cut -f1))"

# Remover backups antigos
REMOVED=$(find "$BACKUP_DIR" -name "otrs-mcp_*.db.gz" -mtime +$KEEP_DAYS -delete -print | wc -l)
if [ "$REMOVED" -gt 0 ]; then
    echo "[Backup] Removidos $REMOVED backups com mais de ${KEEP_DAYS} dias"
fi

echo "[Backup] Concluido"
