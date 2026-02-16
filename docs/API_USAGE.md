# API Usage – World-of-ASR Backend

## Create Transcription

POST `/api/v1/transcribe`

Payload example:

```json
{
  "file_ids": ["<uploaded-file-uuid>"],
  "model_type": "faster_whisper",
  "model_size": "large-v3",
  "language": "auto",
  "device": "cuda",
  "parameters": {
    "initial_prompt": "회의록 형식으로 정리해 주세요.",
    "beam_size": 5,
    "temperature": 0
  },
  "diarization": {"enabled": true, "min_speakers": 1, "max_speakers": 5},
  "output_formats": ["vtt", "json"],
  "force_alignment": false,
  "alignment_provider": "qwen",
  "postprocess": {"pnc": true, "vad": false}
}
```

Notes:
- `language`: use an ISO code (e.g., `ko`, `en`) or `auto` for automatic language detection.
- `parameters.initial_prompt`: forwarded to models that support prompts (e.g., Whisper variants).
- `force_alignment`: when true and the selected provider doesn’t return word timings, the service may apply a forced alignment pass (provider dependent).
- `postprocess`: optional post-processing chain, currently supports `pnc` (punctuation & capitalization) and `vad` (voice activity detection). Stubs are wired and can be swapped with real models.

## Providers

- Local providers (free by default):
  - `origin_whisper`, `faster_whisper`, `fast_conformer` (requires Docker container)
- External providers (optional with API keys; disabled by default):
  - `google_stt` – set `enable_google=true` and credentials via env/ADC.
  - `qwen_asr` – set `enable_qwen=true` and provide API key/endpoint.

Check provider availability:

GET `/health`

```json
{
  "status": "healthy",
  "database": "connected",
  "providers": {
    "google_stt_enabled": false,
    "qwen_asr_enabled": false
  }
}
```

## Upload Files

POST `/api/v1/upload` (multipart/form-data)

- Accepts up to 10 files; defaults: max 500MB each.
- Audio/Video MIME types only.

Response:

```json
{ "file_ids": ["uuid-1"], "uploaded_at": "..." }
```

## Get Job Status

GET `/api/v1/transcribe/jobs/{job_id}`

Returns job status, progress, timestamps, and error (if any).

## Download Results

GET `/api/v1/results/{job_id}/{format}` where `{format}` is one of `vtt|srt|json|txt|tsv`.
- List providers/models/languages

GET `/api/v1/transcribe/providers`

```json
{
  "providers": {
    "origin_whisper": true,
    "faster_whisper": true,
    "fast_conformer": true,
    "google_stt": false,
    "qwen_asr": false
  },
  "models": {
    "origin_whisper": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
    "faster_whisper": ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
    "fast_conformer": ["fast-conformer"]
  },
  "languages": ["auto", "en", "ko", "ja", "zh", "de", "es", "fr", "ru", "it", "pt", "vi", "th"],
  "notes": "External providers require keys; see docs/PROVIDERS.md"
}
```
