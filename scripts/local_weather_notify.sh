#!/usr/bin/env bash
set -euo pipefail

if [[ "${RAMEN_CAFFEINATED:-}" != "1" ]]; then
  export RAMEN_CAFFEINATED=1
  exec /usr/bin/caffeinate -i -s -t 900 "$0" "$@"
fi

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

"$VENV_DIR/bin/python" scripts/weather_notify.py
