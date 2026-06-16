#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="${SESSION_LOG_PATH:-$PROJECT_ROOT/data/sessions.jsonl}"
DST_DIR="${TRAVEL_REC_BACKUP_DIR:-$HOME/.travel-rec-backups}"

mkdir -p "$DST_DIR"
if [ -f "$SRC" ]; then
  cp -a "$SRC" "$DST_DIR/sessions-$(date +%Y%m%d-%H).jsonl"
fi
find "$DST_DIR" -type f -mtime +14 -delete
