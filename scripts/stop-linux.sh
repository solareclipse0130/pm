#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="pm-mvp"

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  docker rm -f "$CONTAINER_NAME" >/dev/null
  printf 'Stopped %s\n' "$CONTAINER_NAME"
else
  printf '%s is not running\n' "$CONTAINER_NAME"
fi
