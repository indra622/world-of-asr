from pathlib import Path
from typing import Any, Optional

import numpy as np
import pyaudio
import soundfile as sf
import torch


TARGET_FORMAT = pyaudio.paInt16
TARGET_RATE = 16000
CHUNK = 4096
CHANNELS = 1
OUTPUT_DIR = Path("output")


def load_vad_iterator():
    loaded: Any = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=True,
        onnx=False,
    )
    model = loaded[0]
    utils = loaded[1]
    vad_iterator_cls = utils[3]
    return vad_iterator_cls(model)


def save_segment(audio_buffer: np.ndarray, start_time: float, end_time: float) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = OUTPUT_DIR / f"speech_from_{start_time:.2f}_to_{end_time:.2f}.wav"
    sf.write(str(filename), audio_buffer, TARGET_RATE)
    return str(filename)


def main() -> None:
    vad_iterator = load_vad_iterator()
    pyaudio_instance = pyaudio.PyAudio()
    stream = None

    audio_buffer = np.array([], dtype=np.int16)
    recording = False
    start_time: Optional[float] = None

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
                    saved_path = save_segment(audio_buffer, start_time, end_time)
                    print(f"Speech segment saved as {saved_path}")
                    audio_buffer = np.array([], dtype=np.int16)
                    start_time = None
                    continue

            if recording:
                audio_buffer = np.concatenate((audio_buffer, data))

    except KeyboardInterrupt:
        print("Stopping...")
    except OSError as exc:
        print(f"Audio device error: {exc}")
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        pyaudio_instance.terminate()


if __name__ == "__main__":
    main()
