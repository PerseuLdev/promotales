#!/bin/bash
# Script de backup do cache SQLite

INSTALL_DIR="/opt/promotales"
BACKUP_DIR="/opt/promotales/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup do SQLite (copia segura mesmo com bot rodando)
sqlite3 "$INSTALL_DIR/data/cache.db" ".backup '$BACKUP_DIR/cache_$DATE.db'"

# Backup do monitored_items.json
cp "$INSTALL_DIR/monitored_items.json" "$BACKUP_DIR/monitored_items_$DATE.json" 2>/dev/null || true

# Remove backups antigos (mais de 7 dias)
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.json" -mtime +7 -delete

echo "Backup criado: $BACKUP_DIR/cache_$DATE.db"
ls -lh $BACKUP_DIR
