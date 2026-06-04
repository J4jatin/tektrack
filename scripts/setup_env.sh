#!/usr/bin/env bash
# =============================================================================
# TekTrack — Environment Setup Script
# Sets up Python venv, installs dependencies, and initialises the database.
# Usage: bash scripts/setup_env.sh
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
REQUIREMENTS="$PROJECT_ROOT/requirements.txt"

echo "============================================"
echo " TekTrack Environment Setup"
echo "============================================"
echo "Project root: $PROJECT_ROOT"

# --- Python version check ---
PYTHON=$(command -v python3 || command -v python)
PY_VERSION=$("$PYTHON" --version 2>&1)
echo "Using: $PY_VERSION"

# --- Create virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/4] Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
else
    echo "[1/4] Virtual environment already exists — skipping."
fi

# --- Activate venv ---
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# --- Install dependencies ---
echo "[2/4] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$REQUIREMENTS"

# --- Initialise database ---
echo "[3/4] Initialising database..."
cd "$PROJECT_ROOT"
python - <<'EOF'
from backend.database import init_db, ingest_xml
from pathlib import Path
init_db()
xml = Path("backend/data/sample_orders.xml")
if xml.exists():
    r = ingest_xml(xml)
    print(f"  DB seeded: inserted={r['inserted']}, updated={r['updated']}, skipped={r['skipped']}")
EOF

# --- Done ---
echo "[4/4] Setup complete."
echo ""
echo "To start the API:      source .venv/bin/activate && uvicorn main:app --reload"
echo "To start the dashboard: source .venv/bin/activate && streamlit run frontend/app.py"
echo "To run tests:          source .venv/bin/activate && pytest tests/ -v"
echo "============================================"
