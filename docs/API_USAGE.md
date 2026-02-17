# API Usage - World-of-ASR Backend

This guide covers the end-to-end REST flow:
1. upload files
2. create transcription job
3. poll job status
4. download results

Base URL (local): `http://localhost:8000`

Before using this guide, start backend and verify health using `docs/RUNBOOK.md`.

## 1) Upload Files

`POST /api/v1/upload` (multipart/form-data)

Notes:
- up to 10 files per request
- default max size: 500MB each
- audio/video MIME types only

Example response:

```json
{ "file_ids": ["uuid-1"], "uploaded_at": "..." }
```

## 2) Create Transcription Job

`POST /api/v1/transcribe`

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
- `language`: ISO code (`ko`, `en`) or `auto`
- `parameters.initial_prompt`: forwarded to prompt-capable models
- `force_alignment`: runs alignment pass when word timings are missing (provider-dependent)
- `postprocess`: optional chain (`pnc`, `vad`)

## 3) Poll Job Status

`GET /api/v1/transcribe/jobs/{job_id}`

Returns:
- `status` (`queued`, `processing`, `completed`, `failed`)
- `progress` (0-100)
- timestamps and error field

## 4) Download Results

Single format:

`GET /api/v1/results/{job_id}/{format}`

`{format}` in `vtt|srt|json|txt|tsv`

Result summary:

`GET /api/v1/results/{job_id}`

## Providers and Capabilities

Provider/status listing:

`GET /api/v1/transcribe/providers`

Health and provider flags:

`GET /health`

Example health response:

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

Provider setup details:
- `docs/PROVIDERS.md`

When requests fail, see:
- `docs/TROUBLESHOOTING.md`

## Common Error Responses

### 400 Bad Request

Typical cause:
- business rule validation failed (unsupported model/provider combination, disabled feature)

Example:

```json
{
  "detail": "Google STT is disabled. Set enable_google=true"
}
```

### 404 Not Found

Typical cause:
- unknown `job_id` or missing result file

Example:

```json
{
  "detail": "Job not found"
}
```

### 422 Unprocessable Entity

Typical cause:
- request schema mismatch (missing required fields, invalid enum value)

Example:

```json
{
  "detail": [
    {
      "loc": ["body", "model_type"],
      "msg": "Input should be one of: origin_whisper, faster_whisper, ...",
      "type": "enum"
    }
  ]
}
```

### 500 Internal Server Error

Typical cause:
- unexpected runtime exception during background processing or file operations

Action:
- check backend logs and then inspect `GET /api/v1/transcribe/jobs/{job_id}` for the job-level error field
