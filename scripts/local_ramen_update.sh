#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${RAMEN_ENV_FILE:-$HOME/.config/ramen-shinten-app/env}"
VENV_DIR="$ROOT/.venv-local"

cd "$ROOT"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  echo "Local env file not found: $ENV_FILE"
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -r requirements.txt
fi

git pull --ff-only origin main

"$VENV_DIR/bin/python" scripts/update_snapshot.py

if ! git diff --quiet -- data/news_snapshot.json; then
  git add data/news_snapshot.json
  git commit -m "Update ramen news snapshot"
  git push origin main
else
  echo "No snapshot changes to commit."
fi
