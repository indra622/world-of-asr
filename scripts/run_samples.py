#!/usr/bin/env python3
"""
Smoke test script for World-of-ASR backend.

Uploads sample files, creates a transcription job, polls status, and downloads a result file.

Usage:
  python scripts/run_samples.py --host http://localhost:8000 \
      --files samples/example.wav --model faster_whisper --model-size large-v3 \
      --language auto --format vtt
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests


def upload_files(base_url: str, files: list[Path]) -> list[str]:
    url = f"{base_url}/api/v1/upload"
    m = []
    for p in files:
        m.append(("files", (p.name, p.open("rb"), "application/octet-stream")))
    r = requests.post(url, files=m, timeout=120)
    r.raise_for_status()
    return r.json()["file_ids"]


def create_job(base_url: str, file_ids: list[str], model: str, model_size: str, language: str, output_format: str, device: str = "cuda") -> str:
    url = f"{base_url}/api/v1/transcribe"
    payload = {
        "file_ids": file_ids,
        "model_type": model,
        "model_size": model_size,
        "language": language,
        "device": device,
        "parameters": {},
        "diarization": {"enabled": False, "min_speakers": 1, "max_speakers": 2},
        "output_formats": [output_format],
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["job_id"]


def poll_job(base_url: str, job_id: str, interval: float = 2.0, timeout: float = 600.0) -> dict:
    url = f"{base_url}/api/v1/transcribe/jobs/{job_id}"
    start = time.time()
    while True:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        prog = data.get("progress")
        print(f"Job {job_id} status={status} progress={prog}%")
        if status in ("completed", "failed", "cancelled"):
            return data
        if time.time() - start > timeout:
            raise TimeoutError("Job polling timed out")
        time.sleep(interval)


def download_result(base_url: str, job_id: str, fmt: str, out_dir: Path) -> Path:
    url = f"{base_url}/api/v1/results/{job_id}/{fmt}"
    r = requests.get(url, timeout=120)
    if r.status_code != 200:
        print(f"Failed to download result: {r.status_code} {r.text}")
        r.raise_for_status()
    out_dir.mkdir(parents=True, exist_ok=True)
    # filename from header fallback
    filename = r.headers.get("content-disposition", f"{job_id}.{fmt}")
    if "filename=" in filename:
        filename = filename.split("filename=")[-1].strip("\"")
    out_path = out_dir / filename
    out_path.write_bytes(r.content)
    return out_path


def normalize_text(s: str) -> str:
    # Lowercase, collapse whitespace
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_text_from_file(path: Path, fmt: str) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if fmt == "txt":
        return text
    if fmt in ("vtt", "srt"):
        # Remove timestamps and indices
        lines = []
        for line in text.splitlines():
            if re.match(r"^\s*\d+\s*$", line):
                continue
            if "-->" in line:
                continue
            if line.strip().upper() == "WEBVTT":
                continue
            if not line.strip():
                continue
            lines.append(line)
        return "\n".join(lines)
    if fmt == "json":
        try:
            data = json.loads(text)
            segs = data.get("segments", [])
            return "\n".join(seg.get("text", "") for seg in segs)
        except Exception:
            return text
    if fmt == "tsv":
        # skip header, take 3rd column
        lines = []
        for i, line in enumerate(text.splitlines()):
            if i == 0 and line.startswith("start\tend\t"):
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                lines.append(parts[2])
        return "\n".join(lines)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://localhost:8000")
    ap.add_argument("--files", nargs="+", type=Path, required=True)
    ap.add_argument("--model", default="faster_whisper", choices=[
        "origin_whisper", "faster_whisper", "fast_conformer", "google_stt", "qwen_asr"
    ])
    ap.add_argument("--model-size", default="large-v3")
    ap.add_argument("--language", default="auto")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--format", default="vtt", choices=["vtt", "srt", "json", "txt", "tsv"]) 
    ap.add_argument("--out", type=Path, default=Path("samples/output"))
    ap.add_argument("--expect", type=Path, default=None, help="Optional expected transcript .txt; if omitted, tries <file>_expected.txt")
    args = ap.parse_args()

    base = args.host.rstrip("/")
    for p in args.files:
        if not p.exists():
            print(f"File not found: {p}")
            sys.exit(1)

    try:
        fids = upload_files(base, args.files)
        print("Uploaded:", fids)
        job_id = create_job(base, fids, args.model, args.model_size, args.language, args.format, args.device)
        print("Job created:", job_id)
        info = poll_job(base, job_id)
        print("Final status:", json.dumps(info, ensure_ascii=False))
        if info.get("status") != "completed":
            sys.exit(2)
        out_path = download_result(base, job_id, args.format, args.out)
        print("Saved:", out_path)

        # Optional comparison
        exp = args.expect
        if exp is None:
            # derive from first file name
            stem = args.files[0].with_suffix("")
            exp = stem.with_name(stem.name + "_expected.txt")
        if exp.exists():
            produced = extract_text_from_file(out_path, args.format)
            expected = exp.read_text(encoding="utf-8", errors="ignore")
            n_prod = normalize_text(produced)
            n_exp = normalize_text(expected)
            # crude similarity: ratio of overlap length to expected length
            common = set(n_exp.split()) & set(n_prod.split())
            score = 0.0
            if n_exp:
                score = len(common) / max(1.0, len(set(n_exp.split()))) * 100.0
            print(f"Comparison vs {exp}: ~{score:.1f}% word overlap")
        else:
            print(f"No expected file found at {exp}, skipping comparison")
    except Exception as e:
        print("Error:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
