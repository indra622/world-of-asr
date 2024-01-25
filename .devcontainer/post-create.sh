#!/bin/bash

# Install OpenAI and Dotenv for Python
# TODO: Check why this can't be done in requirements.txt
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
# Install the OpenAI packages for Node.js
# (Python related dependencies are covered in requirements.txt)
# echo "Installing OpenAI For Node.js" 
