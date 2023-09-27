FROM nvcr.io/nvidia/nemo:23.06

WORKDIR /root
ADD run_nemo.py .
ADD download_nemo_models.py .
RUN python -m pip install ujson
RUN python download_nemo_models.py

#ENTRYPOINT ["python", "download_nemo_models.py"]

#CMD ["tail"", "-f", "/dev/null]