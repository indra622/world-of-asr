#!/bin/bash
pip install whisper-timestamped
pip install librosa
pip install docker==6.1.3
pip install gradio==3.45.1
pip install ffmpeg-python
pip install auditok
pip install lightning
pip install torchaudio
pip install einops
pip install pyannote.audio
pip install faster-whisper
sudo apt update && sudo apt install -y ffmpeg
export IP_ADDR=$(hostname -i)
