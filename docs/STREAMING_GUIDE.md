# Streaming Guide - World-of-ASR

## Current Implementation Map

### Server
- Entry: `streaming/whisper_online_server.py`
- Core loop:
  1. receives raw PCM16 chunks over TCP socket
  2. converts bytes to mono 16k waveform
  3. pushes waveform into `OnlineASRProcessor`
  4. emits committed transcript lines with begin/end timestamps

### Streaming Processor
- Core: `streaming/whisper_online.py`
- Main classes:
  - `FasterWhisperASR` / `WhisperTimestampedASR`: backend adapters
  - `OnlineASRProcessor`: rolling audio buffer + prompt/context handling
  - `HypothesisBuffer`: stabilizes partial hypotheses and commits confirmed text

### Client
- Interactive mic client: `sock_streaming_client.py`
- Helper launcher: `scripts/streaming_client.sh`

### WebSocket Server (library-backed)
- Entry: `streaming/whisper_ws_server.py`
- Transport: `websockets` library
- Helper launcher: `scripts/streaming_ws_server.sh`
- Message contract:
  - server -> client ready: `{"type":"ready","sample_rate":16000}`
  - server -> client final transcript: `{"type":"final","beg_ms":...,"end_ms":...,"text":"..."}`
  - client -> server audio: binary PCM16LE mono 16k chunk
  - client -> server flush: text message `flush`

### Experimental Scripts
- `multi_triton_streaming.py`: multiprocessing + Triton path prototype
- `streaming_audio_save.py`: VAD-triggered segment capture utility

## Quick Start

Install streaming dependencies:

```bash
pip install -r requirements-streaming.txt
```

Terminal 1 - start server:

```bash
bash scripts/streaming_server.sh
```

WebSocket variant:

```bash
bash scripts/streaming_ws_server.sh
```

Terminal 2 - start mic client:

```bash
bash scripts/streaming_client.sh
```

Defaults:
- host: `127.0.0.1`
- port: `43007`
- model: `large-v2`
- backend: `faster-whisper`

WebSocket default port:
- `43008`

You can override via env vars:
- `STREAM_HOST`, `STREAM_PORT`, `STREAM_MODEL`, `STREAM_LANG`, `STREAM_BACKEND`, `STREAM_MIN_CHUNK`
- WebSocket port: `STREAM_WS_PORT`

## Recommended Active-Use Profile

For practical low-latency usage:
- keep chunk window small but stable (`STREAM_MIN_CHUNK=0.2` to `0.5`)
- use one backend path consistently (`faster-whisper` recommended for speed)
- avoid running multiple streaming experiment scripts at the same time
- use CPU/GPU profile consistently during a session to avoid warmup spikes

Example:

```bash
STREAM_MODEL=small STREAM_LANG=ko STREAM_MIN_CHUNK=0.3 bash scripts/streaming_server.sh
```

WebSocket example:

```bash
STREAM_MODEL=small STREAM_LANG=ko STREAM_MIN_CHUNK=0.3 STREAM_WS_PORT=43008 bash scripts/streaming_ws_server.sh
```

## Output Semantics

Server emits timestamped committed text lines in this shape:

```text
<beg_ms> <end_ms> <text>
```

This is committed output, not every unstable partial token.

## Operational Notes

- The current server is TCP socket based, not FastAPI WebSocket endpoint yet.
- `streaming/whisper_online_server.py` currently defaults host from `IP_ADDR` env when direct script arg is omitted.
- Roadmap for full WebSocket-first streaming is tracked in `docs/ROADMAP.md` (Phase 4 section).
- `streaming/whisper_ws_server.py` reuses the same `OnlineASRProcessor` with `websockets` transport and sends committed transcript events in JSON.

## Production-Oriented Streaming Checklist

- Keep chunk duration stable in 100-200ms range for low-latency interactive response.
- Treat interim hypotheses as display-only; trigger downstream actions from committed/final text.
- Add reconnect with exponential backoff and local audio ring buffer for outage tolerance.
- Monitor p95 chunk-to-text latency and tune chunk size dynamically when queueing grows.
- Keep one ASR backend path per session to reduce warmup/variance.

## Troubleshooting

For common failures, start with:
- `docs/TROUBLESHOOTING.md` -> Streaming Path Failures section
