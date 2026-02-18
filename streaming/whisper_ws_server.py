#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import time

import numpy as np
import websockets

from whisper_online import (
    FasterWhisperASR,
    OnlineASRProcessor,
    WhisperTimestampedASR,
    create_tokenizer,
    load_audio_chunk,
)


SAMPLING_RATE = 16000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default=os.environ.get("STREAM_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("STREAM_PORT", "43008")))
    parser.add_argument("--min-chunk-size", type=float, default=0.2)
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("STREAM_MODEL", "large-v2"),
        choices="tiny.en,tiny,base.en,base,small.en,small,medium.en,medium,large-v1,large-v2,large".split(","),
    )
    parser.add_argument("--model_cache_dir", type=str, default=None)
    parser.add_argument("--model_dir", type=str, default=None)
    parser.add_argument("--lang", "--language", type=str, default=os.environ.get("STREAM_LANG", "ko"))
    parser.add_argument("--task", type=str, default="transcribe", choices=["transcribe", "translate"])
    parser.add_argument(
        "--backend",
        type=str,
        default=os.environ.get("STREAM_BACKEND", "faster-whisper"),
        choices=["faster-whisper", "whisper_timestamped"],
    )
    parser.add_argument("--vad", action="store_true", default=False)
    return parser.parse_args()


def load_asr(args: argparse.Namespace):
    t0 = time.time()
    if args.backend == "faster-whisper":
        asr_cls = FasterWhisperASR
    else:
        asr_cls = WhisperTimestampedASR

    asr = asr_cls(
        modelsize=args.model,
        lang=args.lang,
        cache_dir=args.model_cache_dir,
        model_dir=args.model_dir,
    )

    if args.task == "translate":
        asr.set_translate_task()
        target_lang = "en"
    else:
        target_lang = args.lang

    if args.vad:
        asr.use_vad()

    demo_audio_path = "2086-149220-0033.wav"
    if os.path.exists(demo_audio_path):
        warmup_audio = load_audio_chunk(demo_audio_path, 0, 1)
        asr.transcribe(warmup_audio)

    elapsed = round(time.time() - t0, 2)
    print(f"ASR loaded in {elapsed}s ({args.backend}, {args.model}, {target_lang})")
    return asr, target_lang


def format_result(result):
    beg_s, end_s, text = result
    if beg_s is None:
        return None
    return {
        "type": "final",
        "beg_ms": int(beg_s * 1000),
        "end_ms": int(end_s * 1000),
        "text": text,
    }


async def run_server(args: argparse.Namespace) -> None:
    asr, target_lang = load_asr(args)
    tokenizer = create_tokenizer(target_lang)
    asr_lock = asyncio.Lock()
    min_chunk_bytes = int(args.min_chunk_size * SAMPLING_RATE * 2)

    async def handler(websocket):
        processor = OnlineASRProcessor(asr, tokenizer)
        processor.init()
        pcm_buffer = bytearray()

        try:
            await websocket.send(json.dumps({"type": "ready", "sample_rate": SAMPLING_RATE}))
            async for message in websocket:
                if isinstance(message, str):
                    if message.strip().lower() == "flush":
                        async with asr_lock:
                            final = await asyncio.to_thread(processor.finish)
                        payload = format_result(final)
                        if payload is not None:
                            await websocket.send(json.dumps(payload, ensure_ascii=False))
                    continue

                pcm_buffer.extend(message)
                while len(pcm_buffer) >= min_chunk_bytes:
                    chunk = bytes(pcm_buffer[:min_chunk_bytes])
                    del pcm_buffer[:min_chunk_bytes]

                    audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                    processor.insert_audio_chunk(audio)

                    async with asr_lock:
                        result = await asyncio.to_thread(processor.process_iter)

                    payload = format_result(result)
                    if payload is not None:
                        await websocket.send(json.dumps(payload, ensure_ascii=False))

        except websockets.ConnectionClosed:
            pass

    print(f"WebSocket streaming server listening on ws://{args.host}:{args.port}")
    async with websockets.serve(handler, args.host, args.port, max_size=4 * 1024 * 1024):
        await asyncio.Future()


def main() -> None:
    args = parse_args()
    asyncio.run(run_server(args))


if __name__ == "__main__":
    main()
