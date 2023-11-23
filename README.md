# World-of-ASR


# Installation


```
sudo apt install ffmpeg
conda create --name woa python=3.11
conda activate woa
git clone https://github.com/indra622/world-of-asr.git
pip install -r requirements.txt
```

If you want to use Nvidia-NeMo,
```
cd docker
docker build -t woa:v1.0 .
docker run -d --gpus 0 -it --name nvidia-nemo -v /tmp/gradio:/tmp/gradio woa:v1.0 tail -f /dev/null

```
and define some environment variables in your .bashrc

```
# in your .bashrc,
export IP_ADDR=$(hostname -i)
export CONTAINER_ID=$(docker ps -q -f name=nvidia-nemo)
export HF_TOKEN="[YOUR_HF_TOKEN]"
```


## Streaming


It is from [ufal/whisper_streaming](https://github.com/ufal/whisper_streaming)

```
pip install -r requirements-streamiing.txt

cd streaming && python whisper_online_server.py
```


# Running

```
python app.py
```


