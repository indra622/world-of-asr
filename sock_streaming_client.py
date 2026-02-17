import os
import queue
import socket
import threading
import tkinter as tk
from typing import Optional, Tuple

import pyaudio
from dotenv import load_dotenv


load_dotenv()

TARGET_FORMAT = pyaudio.paInt16
TARGET_RATE = 16000
CHUNK = 8192
CHANNELS = 1

HOST = os.environ.get("STREAM_HOST", "127.0.0.1")
PORT = int(os.environ.get("STREAM_PORT", "43007"))


class StreamingClientApp:
    def __init__(self) -> None:
        self.host = HOST
        self.port = PORT
        self.stop_event = threading.Event()
        self.pyaudio_instance = pyaudio.PyAudio()
        self.sock: Optional[socket.socket] = None
        self.send_thread: Optional[threading.Thread] = None
        self.recv_thread: Optional[threading.Thread] = None
        self.message_queue: "queue.Queue[Tuple[str, str]]" = queue.Queue()

        self.root = tk.Tk()
        self.root.title("Audio Streaming Client")
        self.switch_var = tk.BooleanVar(value=False)

        self.text_result = tk.Text(self.root, wrap=tk.WORD, width=50, height=15)
        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self._drain_messages)

        self.log("Warming up connection....")
        self._warmup_connection()

    def _build_ui(self) -> None:
        switch = tk.Checkbutton(
            self.root,
            text="Toggle Switch",
            variable=self.switch_var,
            command=self.switch_toggled,
        )
        switch.pack(pady=20)

        start_button = tk.Button(self.root, text="Start", command=self.start_audio)
        start_button.pack(pady=20)

        stop_button = tk.Button(self.root, text="Stop", command=self.stop_audio)
        stop_button.pack(pady=20)

        clear_button = tk.Button(
            self.root,
            text="Clear",
            command=lambda: self.text_result.delete(1.0, tk.END),
        )
        clear_button.pack(pady=20)

        self.text_result.pack(pady=10)

    def _drain_messages(self) -> None:
        try:
            while True:
                kind, message = self.message_queue.get_nowait()
                if kind == "log":
                    self.text_result.insert(tk.END, f"[LOG]{message}\n")
                else:
                    self.text_result.insert(tk.END, f"{message}\n")
                self.text_result.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._drain_messages)

    def log(self, message: str) -> None:
        self.message_queue.put(("log", message))

    def push_result(self, message: str) -> None:
        self.message_queue.put(("result", message))

    def _warmup_connection(self) -> None:
        warmup_socket: Optional[socket.socket] = None
        try:
            warmup_socket = socket.create_connection((self.host, self.port), timeout=2.0)
            if warmup_socket.fileno() != -1:
                warmup_socket.shutdown(socket.SHUT_RDWR)
            self.log("Ready to work!")
        except OSError as exc:
            self.log(f"Connection failed: {exc}")
        finally:
            if warmup_socket is not None:
                warmup_socket.close()

    def _close_socket(self) -> None:
        if self.sock is None:
            return
        try:
            if self.sock.fileno() != -1:
                self.sock.shutdown(socket.SHUT_RDWR)
        except OSError as exc:
            self.log(f"Error during shutdown: {exc}")
        finally:
            self.sock.close()
            self.sock = None

    def send_audio(self) -> None:
        sock = self.sock
        if sock is None:
            self.log("Socket is not connected")
            return

        stream = None
        try:
            stream = self.pyaudio_instance.open(
                format=TARGET_FORMAT,
                channels=CHANNELS,
                rate=TARGET_RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
            while not self.stop_event.is_set():
                data = stream.read(CHUNK, exception_on_overflow=False)
                sock.sendall(data)
        except OSError as exc:
            self.log(f"Audio send error: {exc}")
            self.stop_event.set()
        finally:
            if stream is not None:
                stream.stop_stream()
                stream.close()

    def receive_results(self) -> None:
        sock = self.sock
        if sock is None:
            self.log("Socket is not connected")
            return

        try:
            while not self.stop_event.is_set():
                try:
                    response = sock.recv(CHUNK)
                except socket.timeout:
                    continue

                if not response:
                    self.log("Server closed the connection")
                    self.stop_event.set()
                    break

                output = response.decode(errors="replace").replace("\x00", "").strip()
                if output:
                    self.push_result(output)
        except OSError as exc:
            self.log(f"Receive error: {exc}")
            self.stop_event.set()

    def start_audio(self) -> None:
        if self.sock is not None and self.sock.fileno() != -1:
            self.log("Already connected")
            return

        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=3.0)
            self.sock.settimeout(0.5)
        except OSError as exc:
            self.log(f"Failed to connect: {exc}")
            self.sock = None
            self.switch_var.set(False)
            return

        self.stop_event.clear()
        self.log("Connected to server....")

        self.send_thread = threading.Thread(target=self.send_audio, daemon=True)
        self.recv_thread = threading.Thread(target=self.receive_results, daemon=True)
        self.send_thread.start()
        self.recv_thread.start()

    def stop_audio(self) -> None:
        self.stop_event.set()
        self.log("Disconnecting from server...")

        if self.send_thread is not None:
            self.send_thread.join(timeout=1)
            self.send_thread = None
        if self.recv_thread is not None:
            self.recv_thread.join(timeout=1)
            self.recv_thread = None

        self._close_socket()
        self.stop_event.clear()
        self.log("Disconnected!")

    def switch_toggled(self) -> None:
        if self.switch_var.get():
            self.log("Switch ON")
            self.start_audio()
            return
        self.log("Switch OFF")
        self.stop_audio()

    def on_close(self) -> None:
        self.switch_var.set(False)
        self.stop_audio()
        self.pyaudio_instance.terminate()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    StreamingClientApp().run()
