#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"

if [[ ! -d "$VENV" ]]; then
    echo "Creating virtual environment in .venv..."
    python3 -m venv "$VENV"
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    pip install -r requirements.txt
else
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
fi

if [[ ! -f "$ROOT/.env" ]]; then
    echo "Missing .env — copy .env.example to .env and set DISCORD_TOKEN and DB credentials."
    exit 1
fi

echo "Running database migrations..."
python scripts/migrate.py

echo "Starting Tickr..."
exec python main.py
