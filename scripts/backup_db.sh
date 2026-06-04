#!/usr/bin/env bash
# =============================================================================
# TekTrack — Database Backup Script
# Creates a timestamped backup of the SQLite database.
# Usage: bash scripts/backup_db.sh [backup_dir]
# Recommended: add to cron — 0 2 * * * bash /path/to/tektrack/scripts/backup_db.sh
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_FILE="$PROJECT_ROOT/backend/tektrack.db"
BACKUP_DIR="${1:-$PROJECT_ROOT/backups}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/tektrack_backup_$TIMESTAMP.db"

# Check DB exists
if [ ! -f "$DB_FILE" ]; then
    echo "WARNING: Database not found at $DB_FILE — skipping backup."
    exit 0
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# SQLite hot backup (safe under concurrent writes via WAL mode)
sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"

BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup created: $BACKUP_FILE ($BACKUP_SIZE)"

# Retain only the last 30 backups
BACKUP_COUNT=$(ls "$BACKUP_DIR"/tektrack_backup_*.db 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 30 ]; then
    OLDEST=$(ls -t "$BACKUP_DIR"/tektrack_backup_*.db | tail -1)
    rm "$OLDEST"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Removed oldest backup: $OLDEST"
fi
