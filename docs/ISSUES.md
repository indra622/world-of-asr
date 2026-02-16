# World-of-ASR – Issues & Remediation Plan

This document tracks known issues, risks, and planned remediations across code quality, security, and functionality. Status is updated as work progresses.

## Legend
- Severity: critical | high | medium | low
- Status: open | in-progress | resolved | wontfix

## Security

- Title: Docker exec command injection risk
  - Severity: critical
  - Location: `woa/events.py`, `backend/app/core/models/fast_conformer.py`
  - Problem: `container.exec_run(f"python run_nemo.py {audio_path}")` builds a shell-like command that may mis-handle paths with spaces or special characters.
  - Plan: Pass arguments as a list (no shell), or escape/quote reliably. Ensure `run_nemo.py` accepts explicit argv and outputs strict JSON.
  - Status: open

- Title: Secrets and .env in repository
  - Severity: high
  - Location: `backend/.env`
  - Problem: Environment file is versioned; secrets can leak.
  - Plan: Remove from VCS, keep `backend/.env.example` only, add `backend/.env` to `.gitignore` and rotate any exposed secrets.
  - Status: in-progress

- Title: CORS configuration overly permissive with credentials
  - Severity: medium
  - Location: `backend/app/main.py`
  - Problem: `allow_credentials=True` with broad methods/headers; must tightly scope `allowed_origins` per environment.
  - Plan: Parameterize per-env CORS, disable credentials unless strictly required.
  - Status: open

- Title: Upload content-type/extension validation
  - Severity: medium
  - Location: `backend/app/api/v1/upload.py`
  - Problem: Accepts any file type; should restrict to audio/video MIME/extension whitelist.
  - Plan: Add MIME/extension validation and clear error messages.
  - Status: open

- Title: Default secret key
  - Severity: low
  - Location: `backend/app/config.py`
  - Problem: Dev default is present; enforce override in production.
  - Plan: Fail-fast if using default in non-dev.
  - Status: open

## Data Model / API Mismatch

- Title: JobStatus value mismatch
  - Severity: high
  - Location: `backend/app/services/transcription.py`, `backend/app/db/models.py`, `backend/app/schemas/transcription.py`
  - Problem: Service references `PENDING` while enum defines `QUEUED`.
  - Plan: Unify enums in one place and update references.
  - Status: open

- Title: Relationship/field name mismatch
  - Severity: high
  - Location: Services and models
  - Problem: Service uses `job.files`, `file.filename`, `file.file_path`, `result.output_paths`; model defines `uploaded_files`, `original_filename`, `storage_path`, and per-format columns.
  - Plan: Align model fields with service, or adapt service to current schema; choose a single approach.
  - Status: open

- Title: Response schema mismatch
  - Severity: high
  - Location: `backend/app/api/v1/transcribe.py`, `backend/app/schemas/transcription.py`
  - Problem: Returns `error_message`, `files_count` while schema expects `error`, etc.
  - Plan: Align API responses with Pydantic schemas.
  - Status: open

- Title: Results path handling
  - Severity: medium
  - Location: Results service/routes
  - Problem: Code expects `output_paths` dict on `Result`; model stores per-format paths.
  - Plan: Choose dict/json column or keep per-format columns and query accordingly; update usage.
  - Status: open

## Runtime & Stability

- Title: Streaming server variable scope
  - Severity: medium
  - Location: `streaming/whisper_online_server.py`
  - Problem: Uses `online.process_iter()` instead of `self.online_asr_proc` in class method.
  - Plan: Use instance field consistently.
  - Status: open

- Title: Silent exception swallowing in client
  - Severity: low
  - Location: `sock_streaming_client.py`
  - Problem: Broad `except: pass` hides errors.
  - Plan: Log exceptions with context; avoid bare except.
  - Status: open

- Title: Health endpoint does not verify DB
  - Severity: low
  - Location: `backend/app/main.py`
  - Problem: Returns healthy without checking DB connection.
  - Plan: Add simple query or connection ping.
  - Status: open

## Code Quality / Dependencies

- Title: `asyncio` pinned as dependency
  - Severity: medium
  - Location: `backend/requirements.txt`
  - Problem: Standard library; pinning a backport may cause conflicts.
  - Plan: Remove unless truly needed.
  - Status: open

- Title: Declarative base import deprecation
  - Severity: low
  - Location: `backend/app/db/base.py`
  - Problem: Use `sqlalchemy.orm.declarative_base` in newer SQLAlchemy.
  - Plan: Update import.
  - Status: open

- Title: Duplicate enums and formatters
  - Severity: low
  - Location: `schemas` vs `db`; `woa/utils.py` vs `backend/app/core/processors/formatters.py`
  - Problem: Divergence risk.
  - Plan: Consolidate to single source of truth.
  - Status: open

## Notes
- Model cache is per-process; document behavior for multi-worker deployments.
- Heavy ML deps increase image size; consider split extras (cpu/gpu) and optional installs.

