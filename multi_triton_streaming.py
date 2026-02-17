import json
import os
from multiprocessing import Pipe, Process
from typing import Any

import numpy as np
import pyaudio
import torch
from tritonclient.http import InferInput, InferenceServerClient


TARGET_FORMAT = pyaudio.paInt16
TARGET_RATE = 16000
CHUNK = 8192
CHANNELS = 1

TRITON_URL = os.environ.get("TRITON_URL", "127.0.0.1:8123")
TRITON_MODEL_NAME = os.environ.get("TRITON_MODEL_NAME", "whisper-large")


def receiver(conn) -> None:
    try:
        triton_client = InferenceServerClient(url=TRITON_URL, network_timeout=3600)
    except Exception as exc:
        print(f"Failed to initialize Triton client: {exc}")
        return

    while True:
        try:
            audio = conn.recv()
        except EOFError:
            break
        except OSError as exc:
            print(f"Pipe receive error: {exc}")
            break

        if isinstance(audio, str) and audio == "END":
            break
        if not isinstance(audio, np.ndarray):
            print(f"Unexpected payload type: {type(audio)}")
            continue

        try:
            audio_input = InferInput(name="audio", shape=audio.shape, datatype="FP32")
            sr_input = InferInput(name="sample_rate", shape=[1], datatype="INT32")
            audio_input.set_data_from_numpy(audio)
            sr_input.set_data_from_numpy(np.array([TARGET_RATE], dtype=np.int32))

            result = triton_client.infer(
                model_name=TRITON_MODEL_NAME,
                inputs=[audio_input, sr_input],
                timeout=360000,
            )
            transcripts = result.as_numpy("transcription")
            parsed = json.loads(transcripts[0])
            print(parsed)
        except Exception as exc:
            print(f"Triton inference error: {exc}")

    conn.close()


def sender(conn) -> None:
    pyaudio_instance = pyaudio.PyAudio()
    stream = None

    try:
        loaded: Any = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=True,
            onnx=False,
        )
        model = loaded[0]
        utils = loaded[1]
        vad_iterator_cls = utils[3]
        vad_iterator = vad_iterator_cls(model)
    except Exception as exc:
        print(f"Failed to load VAD model: {exc}")
        conn.send("END")
        conn.close()
        pyaudio_instance.terminate()
        return

    audio_buffer = np.array([], dtype=np.int16)
    recording = False
    start_time = None

    try:
        stream = pyaudio_instance.open(
            format=TARGET_FORMAT,
            channels=CHANNELS,
            rate=TARGET_RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        print("Listening...")

        while True:
            data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
            segment = vad_iterator(data, return_seconds=True)

            if segment is not None:
                if "start" in segment:
                    if not recording:
                        start_time = float(segment["start"])
                        recording = True
                        audio_buffer = np.array([], dtype=np.int16)
                    audio_buffer = np.concatenate((audio_buffer, data))
                    continue

                if "end" in segment and recording and start_time is not None:
                    end_time = float(segment["end"])
                    recording = False
                    print(f"Speech segment captured: {start_time:.2f} -> {end_time:.2f}")

                    audio = audio_buffer.astype(np.float32).reshape(1, -1)
                    conn.send(audio)

                    audio_buffer = np.array([], dtype=np.int16)
                    start_time = None
                    continue

            if recording:
                audio_buffer = np.concatenate((audio_buffer, data))

    except KeyboardInterrupt:
        print("Stopping sender...")
    except (OSError, RuntimeError) as exc:
        print(f"Sender error: {exc}")
    finally:
        try:
            conn.send("END")
        except OSError:
            pass
        conn.close()
        if stream is not None:
            stream.stop_stream()
            stream.close()
        pyaudio_instance.terminate()


if __name__ == "__main__":
    parent_conn, child_conn = Pipe()

    receiver_process = Process(target=receiver, args=(child_conn,))
    sender_process = Process(target=sender, args=(parent_conn,))

    receiver_process.start()
    sender_process.start()

    sender_process.join()
    receiver_process.join()
