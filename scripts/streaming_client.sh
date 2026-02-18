#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f backend/.env ]; then
  set -a
  . backend/.env
  set +a
fi

python sock_streaming_client.py
