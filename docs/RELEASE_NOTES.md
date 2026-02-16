# World-of-ASR – Release Notes (Work-in-Progress)

## Summary (current iteration)

- Backend refactor for schema/ORM/service alignment.
- Security hardening: upload validation, Docker exec argv, health DB check.
- Multi-provider scaffolding: Google STT, Qwen ASR, forced alignment hooks.
- Language `auto`, prompt forwarding, alignment options.
- Docs: API usage, providers, runbook, issues, progress; samples + smoke tests.
- Gradio: Backend API tab to drive FastAPI endpoints.
- CI: minimal unit test workflow for formatters/basic.

See `docs/PROGRESS.md` for detailed daily logs.

## Breaking changes

- Result model paths stored per-format columns (json/vtt/srt/txt/tsv).
- Service uses `uploaded_files` relation; request schema extended.

## Next

- Implement Google/Qwen adapters with real API calls (keys required).
- NVIDIA NeMo/Triton adapters and post-processing chain (PnC/VAD) integration.

