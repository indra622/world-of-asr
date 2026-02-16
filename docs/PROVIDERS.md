# External ASR Providers

World-of-ASR supports optional external ASR providers. They are disabled by default and can be enabled via environment variables.

## Google Cloud Speech-to-Text (v2)

- Enable:
  - In `backend/.env` set:
    - `ENABLE_GOOGLE=true`
    - `GOOGLE_PROJECT_ID=<your_project>`
    - `GOOGLE_LOCATION=global` (or your region)
    - `GOOGLE_API_KEY=<optional>` or use ADC (service account credentials)
- Install deps:
  - `pip install google-cloud-speech`
- Notes:
  - Authentication is handled via Application Default Credentials or service account key file.
  - Current implementation is a stub; wire actual API calls in `backend/app/core/models/google_stt.py`.

## Qwen ASR

- Enable:
  - In `backend/.env` set:
    - `ENABLE_QWEN=true`
    - `QWEN_API_KEY=<your_key>`
    - `QWEN_ENDPOINT=<api_endpoint>`
- Install deps as needed for the chosen client.
- Notes:
  - Current implementation is a stub; wire actual API calls in `backend/app/core/models/qwen_asr.py`.

## Forced Alignment (Qwen)

- Request fields:
  - `force_alignment: true`
  - `alignment_provider: "qwen"`
- Implementation placeholder in `backend/app/core/processors/forced_alignment.py`.

