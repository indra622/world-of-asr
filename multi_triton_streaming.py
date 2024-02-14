import time
from multiprocessing import Process, Pipe

# 오디오 스트림을 받아 발화 구간을 실시간으로 탐지하고, 발화 구간을 파일로 저장하는 예제입니다.

import numpy as np
import pyaudio
import soundfile as sf
import torch
from tritonclient.http import InferenceServerClient, InferInput
import json

TARGET_FORMAT = pyaudio.paInt16  # 목표 포맷 (16-bit)
TARGET_RATE = 16000  # 목표 샘플링 레이트
CHUNK = 8192  # 오디오 청크 크기
CHANNELS = 1  # 채널 수




def receiver(conn):
    url = "10.17.23.228:8123"
    model_name = "whisper-large"

    triton_client = InferenceServerClient(url=url, network_timeout=3600)
    while True:
        audio = conn.recv()  # 메시지 수신 대기
        audio_input = InferInput(name="audio", shape=audio.shape, datatype="FP32")
        sr_input = InferInput(name="sample_rate", shape=[1], datatype="INT32")

        audio_input.set_data_from_numpy(audio)
        sr_input.set_data_from_numpy(np.array([TARGET_RATE], dtype=np.int32))

        result = triton_client.infer(
            model_name=model_name,
            inputs=[audio_input, sr_input],
            timeout=360000,
        )

        transcripts = result.as_numpy("transcription")
        transcripts = json.loads(transcripts[0])

        print(transcripts)
        

def sender(conn):

    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=True,
                              onnx=False)

    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils



    p = pyaudio.PyAudio()
    stream = p.open(format=TARGET_FORMAT, channels=CHANNELS, rate=TARGET_RATE, input=True, frames_per_buffer=CHUNK)
    print("Listening...")

    vad_iterator = VADIterator(model)
    audio_buffer = np.array([], dtype=np.int16)  # 음성 데이터를 저장할 버퍼
    recording = False  # 현재 녹음 중인지 상태를 추적
    start_time = None  # 발화 시작 시간

    while True:
        data = np.frombuffer(stream.read(CHUNK), dtype=np.int16)
        segment = vad_iterator(data, return_seconds=True)
        
        if segment is not None:
            if 'start' in segment:
                # 발화 시작
                if not recording:
                    start_time = segment['start']
                    recording = True
                    audio_buffer = np.array([], dtype=np.int16)  # 새로운 발화에 대해 버퍼 초기화
                audio_buffer = np.concatenate((audio_buffer, data))  # 발화 중 데이터 추가

            elif 'end' in segment and recording:
                # 발화 종료
                end_time = segment['end']
                recording = False
                
                # 파일명 생성 및 오디오 저장
                filename = f"output/speech_from_{start_time:.2f}_to_{end_time:.2f}.wav"
                #sf.write(filename, audio_buffer, TARGET_RATE)
                print(f"Speech segment saved as {filename}")

                # Triton inference
                print(type(audio_buffer), audio_buffer.shape, audio_buffer.dtype)  
                # 자료형 변경
                audio = audio_buffer.astype(np.float32)
                audio = audio.reshape(1, -1)
                # 오디오 데이터 전송
                conn.send(audio)

                audio_buffer = np.array([], dtype=np.int16)  # 버퍼 초기화
                start_time = None

        elif recording:
            # 발화 중인 상태에서 segment가 None이면 계속 데이터 추가
            audio_buffer = np.concatenate((audio_buffer, data))
    conn.send('END')  # 전송 종료 신호

if __name__ == '__main__':
    parent_conn, child_conn = Pipe()
    
    # 리시버 프로세스 생성 및 시작
    p_receiver = Process(target=receiver, args=(child_conn,))
    p_receiver.start()
    
    # 센더 프로세스 생성 및 시작
    p_sender = Process(target=sender, args=(parent_conn,))
    p_sender.start()
    
    # 프로세스들이 종료될 때까지 기다림
    p_sender.join()
    p_receiver.join()



