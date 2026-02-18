#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f backend/.env ]; then
  set -a
  . backend/.env
  set +a
fi

HOST_VALUE="${STREAM_HOST:-${IP_ADDR:-127.0.0.1}}"
PORT_VALUE="${STREAM_WS_PORT:-43008}"
MODEL_VALUE="${STREAM_MODEL:-large-v2}"
LANG_VALUE="${STREAM_LANG:-ko}"
BACKEND_VALUE="${STREAM_BACKEND:-faster-whisper}"
MIN_CHUNK_VALUE="${STREAM_MIN_CHUNK:-0.2}"

python streaming/whisper_ws_server.py \
  --host "${HOST_VALUE}" \
  --port "${PORT_VALUE}" \
  --model "${MODEL_VALUE}" \
  --lang "${LANG_VALUE}" \
  --backend "${BACKEND_VALUE}" \
  --min-chunk-size "${MIN_CHUNK_VALUE}"
