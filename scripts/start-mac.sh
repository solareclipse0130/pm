#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="pm-mvp"
CONTAINER_NAME="pm-mvp"
PORT="${PORT:-9000}"
DATA_DIR="$ROOT_DIR/data"

cd "$ROOT_DIR"
mkdir -p "$DATA_DIR"

docker build -t "$IMAGE_NAME" .

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null
fi

env_args=()
temp_env_file=""
if [ -f "$ROOT_DIR/.env" ]; then
  temp_env_file="$(mktemp)"
  awk '
    /^[[:space:]]*($|#)/ { next }
    {
      eq = index($0, "=")
      if (eq == 0) { next }
      key = substr($0, 1, eq - 1)
      value = substr($0, eq + 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      if (key != "") { print key "=" value }
    }
  ' "$ROOT_DIR/.env" > "$temp_env_file"
  env_args=(--env-file "$temp_env_file")
fi
trap 'if [ -n "$temp_env_file" ]; then rm -f "$temp_env_file"; fi' EXIT

docker run -d \
  --name "$CONTAINER_NAME" \
  -p "${PORT}:8000" \
  -v "${DATA_DIR}:/app/data" \
  "${env_args[@]}" \
  "$IMAGE_NAME"

printf 'Server running at http://localhost:%s\n' "$PORT"
