#!/usr/bin/env bash
# SQLite 每日备份脚本（部署到 VPS 后配合 crontab）
# crontab 示例（每日 16:00 执行）：
#   0 16 * * * /var/www/market-review/deploy/backup.sh
#
# 备份保留最近 30 份

set -e

APP_DIR="/var/www/market-review/api"
BACKUP_DIR="/var/backups/market-review"
DB_FILE="$APP_DIR/data/app.db"

mkdir -p "$BACKUP_DIR"

# 备份（sqlite3 .backup 保证一致性）
STAMP=$(date +%Y%m%d_%H%M)
sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/app_$STAMP.db'" 2>/dev/null || cp "$DB_FILE" "$BACKUP_DIR/app_$STAMP.db"

# 清理 30 天前的备份
find "$BACKUP_DIR" -name "app_*.db" -mtime +30 -delete

echo "[Backup] done: $BACKUP_DIR/app_$STAMP.db"
