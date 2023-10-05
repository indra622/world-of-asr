# World-of-ASR


# Installation


```
sudo apt install ffmpeg
conda create --name woa python=3.11
conda activate woa
git clone https://github.com/indra622/world-of-asr.git
pip install -r requirements.txt
```
```
pip install git+https://github.com/m-bain/whisperx.git@2a11ce3ef07fc888924bf0bc4b080ede983cbe65
```

If you want to use Nvidia-NeMo,
```
cd docker
docker build -t woa:v1.0 .
docker run -d --gpus 0 -it -v /tmp/gradio:/tmp/gradio woa:v1.0 tail -f /dev/null

```
and copy&paste your container id into CONTAINER_ID in events.py 

# Running

```
python app.py
```


