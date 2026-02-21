#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

if [[ -x "$ROOT/dino-ds" ]]; then
  exec "$ROOT/dino-ds" help "$@"
fi

if [[ -x "$ROOT/dino-ds-bin" ]]; then
  exec "$ROOT/dino-ds-bin" help "$@"
fi

echo "ERROR: dino-ds wrapper/binary not found under $ROOT" >&2
exit 1

