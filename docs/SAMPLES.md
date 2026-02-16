# Sample Set and Smoke Test

Place small, public-domain audio clips (10–30s) into `samples/`.

Example structure:

```
samples/
  example.wav
  example_expected.txt   # optional
```

Run smoke test against a running backend:

```bash
python scripts/run_samples.py --host http://localhost:8000 \
  --files samples/example.wav --model faster_whisper --model-size large-v3 \
  --language auto --format vtt --out samples/output
```

Notes:
- For NeMo `fast_conformer`, ensure the Docker container is running and environment is set.
- External providers (`google_stt`, `qwen_asr`) require enabling flags and valid keys in environment (see backend/.env.example); otherwise they remain disabled.

Optional comparison:

- If `samples/example_expected.txt` exists, the script will compare produced transcript to expected and print an approximate word-overlap score.
- Alternatively, provide `--expect path/to/expected.txt`.

Fetch a ready-to-use sample set:

```bash
bash scripts/fetch_samples.sh
```
