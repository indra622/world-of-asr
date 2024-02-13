'''''''''''''''''''''''''''''''''''''''''''''

python sock_streaming_client.py 
for MacOS and Windows

requirements
pyaudio python-dotenv


'''''''''''''''''''''''''''''''''''''''''''''


import socket
import tkinter as tk
import pyaudio
import threading
import numpy as np
from dotenv import load_dotenv
import os

load_dotenv()

TARGET_FORMAT = pyaudio.paInt16  # 목표 포맷 (16-bit)
TARGET_RATE = 16000  # 목표 샘플링 레이트

CHUNK = 8192  # 오디오 청크 크기
CHANNELS = 1  # 스테레오

p = pyaudio.PyAudio()
streaming = False  # 스트리밍 상태를 나타내는 변수

HOST = "127.0.0.1"
PORT = 43007
#HOST = os.environ.get('STREAM_HOST')
#PORT = os.environ.get('STREAM_PORT')

p = pyaudio.PyAudio()

stop_event = threading.Event()

def send_audio():
    stream = p.open(format=TARGET_FORMAT, channels=CHANNELS, rate=TARGET_RATE, input=True, frames_per_buffer=CHUNK)
    
    try:
        while not stop_event.is_set():
            data = stream.read(CHUNK)
            s.sendall(data)
    except:
        pass
    finally:
        stream.stop_stream()
        stream.close()

def receive_results():
    try:
        while True:
            response = s.recv(CHUNK)
            if response:
                output = response.decode().replace('\x00', '').strip()
                if output:
                    text_result.insert(tk.END, f"{output}\n")
                    text_result.see(tk.END)  # 자동 스크롤
    except:
        pass

def start_audio():
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    text_result.insert(tk.END, "[LOG]Connected to server....\n")
    global send_thread, recv_thread
    send_thread = threading.Thread(target=send_audio)
    recv_thread = threading.Thread(target=receive_results)
    send_thread.start()
    recv_thread.start()
    
    

def stop_audio():
    global send_thread, recv_thread
    stop_event.set()
    text_result.insert(tk.END, "[LOG]Disconnecting from server...\n")
    if send_thread:
        send_thread.join(timeout=1)
    if recv_thread:
        recv_thread.join(timeout=1)
    
    try:
        if s.fileno() != -1:
            s.shutdown(socket.SHUT_RDWR)
    except OSError as e:
        print(f"[LOG]Error during shutdown: {e}")
    finally:
        s.close()

    stop_event.clear()
    text_result.insert(tk.END, "[LOG]Disconnected!\n")


def switch_toggled():
    # 스위치 상태에 따라 동작 수행
    if switch_var.get():
        print("Switch ON")
        # 여기에 스위치 켜짐 상태일 때의 코드 추가
        start_audio()
    else:
        print("Switch OFF")
        # 여기에 스위치 꺼짐 상태일 때의 코드 추가
        stop_audio()

app = tk.Tk()
app.title("Audio Streaming Client")

switch_var = tk.BooleanVar()

switch = tk.Checkbutton(app, text="Toggle Switch", var=switch_var, command=switch_toggled)
switch.pack(pady=20)

start_button = tk.Button(app, text="Start", command=start_audio)
start_button.pack(pady=20)

stop_button = tk.Button(app, text="Stop", command=stop_audio)
stop_button.pack(pady=20)

clear_button = tk.Button(app, text="Clear", command=lambda: text_result.delete(1.0, tk.END))
clear_button.pack(pady=20)

text_result = tk.Text(app, wrap=tk.WORD, width=50, height=15)
text_result.pack(pady=10)

text_result.insert(tk.END, "[LOG]Warming up connection....\n")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    try:
        if s.fileno() != -1:
            s.shutdown(socket.SHUT_RDWR)
    except OSError as e:
        print(f"[LOG]Error during shutdown: {e}")
    finally:
        s.close()  
    text_result.insert(tk.END, "[LOG]Ready to work!\n")
except:
    text_result.insert(tk.END, "[LOG]Connection failed...\n")


app.mainloop()

p.terminate()

