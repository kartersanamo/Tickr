#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.dashboard ]]; then
  echo "Create .env.dashboard from .env.dashboard.example first."
  exit 1
fi

set -a
source .env.dashboard
set +a

docker compose build \
  --build-arg NEXT_PUBLIC_SITE_URL="${NEXT_PUBLIC_SITE_URL:-https://tickr.kartersanamo.com}" \
  --build-arg NEXT_PUBLIC_BOT_INVITE_URL="${NEXT_PUBLIC_BOT_INVITE_URL:-}" \
  --build-arg NEXT_PUBLIC_DISCORD_CLIENT_ID="${DISCORD_CLIENT_ID:-}"

docker compose up -d

echo "Tickr dashboard running:"
echo "  Web: http://localhost:8005"
echo "  API: http://localhost:8790"
