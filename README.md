# World-of-ASR


# Installation


```
conda create --name woa python=3.11
conda activate woa
pip install -r requirements.txt
```
```
$pip install git+https://github.com/m-bain/whisperx.git@v3.1.1
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


