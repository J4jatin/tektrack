#!/usr/bin/env bash
# =============================================================================
# TekTrack — XML Ingestion Script
# Parses an XML orders file and loads/updates records into the SQLite database.
# Usage: bash scripts/ingest.sh [path/to/orders.xml]
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XML_FILE="${1:-$PROJECT_ROOT/backend/data/sample_orders.xml}"

# Validate file exists
if [ ! -f "$XML_FILE" ]; then
    echo "ERROR: XML file not found: $XML_FILE"
    echo "Usage: bash scripts/ingest.sh [path/to/orders.xml]"
    exit 1
fi

# Validate it looks like XML
if ! head -1 "$XML_FILE" | grep -q "<?xml"; then
    echo "ERROR: File does not appear to be a valid XML file: $XML_FILE"
    exit 1
fi

# Activate venv if present
VENV="$PROJECT_ROOT/.venv/bin/activate"
if [ -f "$VENV" ]; then
    # shellcheck disable=SC1090
    source "$VENV"
fi

echo "============================================"
echo " TekTrack XML Ingestion"
echo " File: $XML_FILE"
echo " Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

cd "$PROJECT_ROOT"
python - <<EOF
import sys
sys.path.insert(0, "$PROJECT_ROOT")
from backend.database import init_db, ingest_xml
from pathlib import Path

init_db()
result = ingest_xml(Path("$XML_FILE"))
print(f"  Inserted : {result['inserted']}")
print(f"  Updated  : {result['updated']}")
print(f"  Skipped  : {result['skipped']}")
print("Ingestion complete.")
EOF

echo "============================================"
