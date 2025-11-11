from email.mime import audio
import logging
import os
import threading

import pyaudio
import requests
from .speech_recorder import SpeechRecorder


logger = logging.getLogger(__name__)


class MicrophoneListener:
    def __init__(self, **kwargs):
        self._is_listening = False
        self._listening_thread: threading.Thread | None = None

        self._recorder_chunk_size: int = kwargs.get("recorder_chunk_size", 4096)
        self._recorder_start_threshold: int = kwargs.get("recorder_start_threshold", 0)
        self._recorder_silence_threshold: int = kwargs.get("recorder_silence_threshold", 0)
        self._recorder_silence_max_frames: int = kwargs.get("recorder_silence_max_frames", 0)

        recorder_args: dict = kwargs.get("recorder_args", {})
        self._recorder: SpeechRecorder = SpeechRecorder(**recorder_args)

    @property
    def is_listening(self) -> bool:
        return self._is_listening and self._listening_thread is not None and self._listening_thread.is_alive()

    def _open_microphone_stream(self) -> pyaudio.Stream:
        """Open microphone audio stream for recording"""

        # Suppress ALSA and audio device warnings during PyAudio instantiation
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr_fd = os.dup(2)
        os.dup2(devnull, 2)
        try:
            mic: pyaudio.PyAudio = pyaudio.PyAudio()
            stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
        finally:
            os.dup2(old_stderr_fd, 2)
            os.close(devnull)
            os.close(old_stderr_fd)

        return stream

    def _listen_loop(self, model: str, duration_seconds: int):
        stream: pyaudio.Stream = self._open_microphone_stream()
        stream.start_stream()
        logger.info("Listening for speech...")

        try:
            buffer_bytes = self._recorder.record_until_speech_end(
                duration_seconds=duration_seconds,
                start_threshold=self._recorder_start_threshold,
                silence_threshold=self._recorder_silence_threshold,
                silence_max_frames=self._recorder_silence_max_frames,
                chunk=self._recorder_chunk_size,
            )
        finally:
            self._recorder.close()

        # Send data to Audio Backend for speech-to-text processing
        audio_backend_host: str = os.getenv("AUDIO_BACKEND_HOST", "")
        audio_backend_port: int = int(os.getenv("AUDIO_BACKEND_PORT", "0"))
        audio_backend_token: str = os.getenv("AUDIO_BACKEND_TOKEN", "")

        audio_backend_url: str = f"{audio_backend_host}:{audio_backend_port}"
        data = buffer_bytes

        # response: requests.Response = requests.post(
        #    f"{audio_backend_url}/speech-to-text",
        #    headers={"Authorization": f"Bearer {audio_backend_token}"},
        #    files={"file": ("recording.raw", data, "application/octet-stream")},
        # )

        # Automatically restart listening if duration is zero (continuous mode) and still listening
        if duration_seconds == 0 and self._is_listening:
            self._is_listening = False
            self._listening_thread = None

            self.start_listening(model=model, duration_seconds=duration_seconds)
        else:
            logger.info("Listening loop ended.")

    def start_listening(self, model: str, duration_seconds: int):
        if self.is_listening:
            return

        self._is_listening = True
        self._listening_thread = threading.Thread(
            target=self._listen_loop,
            args=(model, duration_seconds),
            daemon=True,
        )
        self._listening_thread.start()

    def stop_listening(self):
        if not self.is_listening:
            return

        # Signal the listening loop to stop
        self._is_listening = False

        # Signal the speech-to-text helper to stop its processing
        if self._speech_to_text_helper is not None:
            self._speech_to_text_helper.stop_listening()

        # Wait for the thread to finish with a reasonable timeout
        if self._listening_thread is not None:
            self._listening_thread.join(timeout=2.0)

            if self._listening_thread.is_alive():
                logger.warning("Listening thread did not stop gracefully within timeout")

            self._listening_thread = None

        self._speech_to_text_helper = None
