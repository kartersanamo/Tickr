#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
    cat <<EOF
Usage: $(basename "$0") <command>

  check     Standard lint + format check (same as the IDE)
  strict    All Ruff rules + strict type checking (run when you want depth)
  fix       Auto-fix standard issues and format

Examples:
  ./scripts/lint.sh check
  ./scripts/lint.sh strict
  ./scripts/lint.sh fix
EOF
}

run_pyright_strict() {
    if command -v basedpyright >/dev/null 2>&1; then
        basedpyright --typecheckingmode strict .
    elif command -v pyright >/dev/null 2>&1; then
        pyright --typecheckingmode strict .
    else
        echo "Skipping Pyright (optional: pip install basedpyright)"
    fi
}

case "${1:-}" in
    check)
        ruff check .
        ruff format --check .
        ;;
    strict)
        ruff check . --config ruff.strict.toml
        ruff format --check .
        run_pyright_strict
        ;;
    fix)
        ruff check --fix .
        ruff format .
        ;;
    -h | --help | help)
        usage
        ;;
    *)
        usage >&2
        exit 1
        ;;
esac
