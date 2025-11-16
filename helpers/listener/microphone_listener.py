import io
import wave
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

        self._recorder_chunk_size = kwargs.get("recorder_chunk_size", 4096)
        self._recorder_start_threshold = kwargs.get("recorder_start_threshold", 0)
        self._recorder_silence_threshold = kwargs.get("recorder_silence_threshold", 0)
        self._recorder_silence_max_frames = kwargs.get("recorder_silence_max_frames", 0)

        recorder_args = kwargs.get("recorder_args", {})
        self._recorder = SpeechRecorder(**recorder_args)

    def _pcm16le_to_wav(self, pcm_bytes, sample_rate=16000, channels=1):
        """Convert raw PCM 16-bit mono audio to WAV format in memory."""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16 bits = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return wav_buffer.getvalue()

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

    def _playback_ai_answer(self, ai_answer: str):
        # Send action to the Action Runner
        ha_backend_host: str = os.getenv("HA_BACKEND_HOST", "")
        ha_backend_port: int = int(os.getenv("HA_BACKEND_PORT", "0"))
        ha_backend_token: str = os.getenv("HA_BACKEND_TOKEN", "")

        json_data: dict = {"ai_answer": ai_answer}

        logger.info(f"Playing back AI answer: '{ai_answer}'")

        response: requests.Response = requests.post(
            f"{ha_backend_host}:{ha_backend_port}/api/ai/playback",
            headers={"Authorization": f"Bearer {ha_backend_token}", "Accept": "application/json"},
            json=json_data,
        )

        if response.status_code != 200:
            logger.warning(f"Failed to playback AI answer: {response.text}")

    def _handle_converted_audio(self, text: str):
        # Convert text to actions via Language Model Backend
        tta_backend_host: str = os.getenv("TEXT_TO_ACTION_BACKEND_HOST", "")
        tta_backend_port: int = int(os.getenv("TEXT_TO_ACTION_BACKEND_PORT", "0"))
        tta_backend_token: str = os.getenv("TEXT_TO_ACTION_BACKEND_TOKEN", "")

        response: requests.Response = requests.post(
            f"{tta_backend_host}:{tta_backend_port}/text-to-action",
            headers={"Authorization": f"Bearer {tta_backend_token}"},
            json={"text": text},
        )

        if response.status_code != 200:
            logger.warning(f"Text to Action backend returned error: {response.text}")
            return

        # Send action to the Action Runner
        ha_backend_host: str = os.getenv("HA_BACKEND_HOST", "")
        ha_backend_port: int = int(os.getenv("HA_BACKEND_PORT", "0"))
        ha_backend_token: str = os.getenv("HA_BACKEND_TOKEN", "")

        response_data: dict = response.json()
        action: str = response_data.get("action", "")
        params: dict = response_data.get("params", {})
        ai_answer: str = response_data.get("ai_answer", "")

        json_data: dict = {"action": {"name": action, "params": params}}

        logger.info(f"Executing action: '{action}' with params: '{params}'")

        response: requests.Response = requests.post(
            f"{ha_backend_host}:{ha_backend_port}/api/action-runner/run-action",
            headers={"Authorization": f"Bearer {ha_backend_token}", "Accept": "application/json"},
            json=json_data,
        )

        # Playback AI answer if available
        if ai_answer:
            threading.Thread(target=self._playback_ai_answer, args=(ai_answer,)).start()

        if response.status_code != 200:
            logger.warning(f"Failed to execute action: {response.text}")

    def _listen_loop(self, duration_seconds: int):
        try:
            stream: pyaudio.Stream = self._open_microphone_stream()
        except OSError as e:
            logger.error(f"Failed to open microphone stream: {e}")
            self._is_listening = False
            return

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

        # Automatically restart listening if duration is zero (continuous mode) and still listening
        if duration_seconds == 0 and self._is_listening:
            self._is_listening = False
            self._listening_thread = None

            self.start_listening(duration_seconds=duration_seconds)
        else:
            logger.info("Listening loop ended.")

        # Send data to Audio Backend for speech-to-text processing
        audio_backend_host: str = os.getenv("AUDIO_BACKEND_HOST", "")
        audio_backend_port: int = int(os.getenv("AUDIO_BACKEND_PORT", "0"))
        audio_backend_token: str = os.getenv("AUDIO_BACKEND_TOKEN", "")

        audio_backend_url: str = f"{audio_backend_host}:{audio_backend_port}"

        # Enhance audio for better speech recognition
        logger.info("Enhancing audio for speech recognition...")

        wav_bytes = self._pcm16le_to_wav(buffer_bytes, sample_rate=16000, channels=1)
        response = requests.post(
            f"{audio_backend_url}/mixer/speed-up",
            headers={"Authorization": f"Bearer {audio_backend_token}"},
            files={
                "file": ("recording.wav", wav_bytes, "audio/wav"),
                "speed": (None, "1.02", "text/plain"),
            },
        )

        if response.status_code != 200:
            logger.warning(f"Audio enhancement failed: {response.text}")
            return

        # Convert speech to text via Audio Backend
        logger.info("Converting speech to text...")
        buffer_bytes = response.content

        # Send the enhanced WAV audio as-is to the backend
        response = requests.post(
            f"{audio_backend_url}/speech-to-text",
            headers={"Authorization": f"Bearer {audio_backend_token}"},
            files={"file": ("recording.wav", buffer_bytes, "audio/wav")},
        )

        text: str = response.json().get("text", "")
        if not text:
            logger.info("No speech recognized.")
            return

        logger.info(f"Recognized text: '{text}'")

        activation_keywords = os.getenv("ACTIVATION_KEYWORDS", "").split(",")
        for keyword in activation_keywords:
            activation: bool = False
            if text.lower().startswith(keyword.strip().lower()):
                activation = True
                text = text.lower().replace(keyword.strip().lower(), "", 1).strip()
            elif text.lower().endswith(keyword.strip().lower()):
                activation = True
                text = text.lower().rsplit(keyword.strip().lower(), 1)[0].strip()

            if not activation:
                continue

            logger.info(f"Activation keyword '{keyword}' detected.")
            self._handle_converted_audio(text)
            break

    def start_listening(self, duration_seconds: int):
        if self.is_listening:
            return

        self._is_listening = True
        self._listening_thread = threading.Thread(
            target=self._listen_loop,
            args=(duration_seconds,),
            daemon=True,
        )
        self._listening_thread.start()

    def stop_listening(self):
        if not self.is_listening:
            return

        # Signal the listening loop to stop
        self._is_listening = False

        # Signal the speech-to-text helper to stop its processing
        if self._recorder is not None:
            self._recorder.close()

        # Wait for the thread to finish with a reasonable timeout
        if self._listening_thread is not None:
            self._listening_thread.join(timeout=2.0)

            if self._listening_thread.is_alive():
                logger.warning("Listening thread did not stop gracefully within timeout")

            self._listening_thread = None
