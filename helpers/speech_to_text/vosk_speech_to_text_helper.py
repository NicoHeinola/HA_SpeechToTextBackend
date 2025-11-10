#!/usr/bin/env python3
"""
Local Speech-to-Text Helper using Vosk
Provides offline speech recognition without internet connection
"""

import json
import logging
import os
import threading

import pyaudio
from vosk import Model, KaldiRecognizer, SetLogLevel


SetLogLevel(-1)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s]: %(message)s")


class VoskSpeechToTextHelper:
    """
    Local speech-to-text recognition using Vosk
    - Fully offline (no internet required)
    - Low latency
    - Supports multiple languages
    """

    def __init__(self, model_path: str):
        """
        Initialize the speech-to-text helper

        Args:
            model_path: Path to Vosk model directory. Can also be a name of a pre-downloaded model in the "models/audio/vosk/" directory
        """
        if not os.path.exists(model_path):
            model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "audio", "vosk", model_path)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Vosk model not found at {model_path}\n"
                f"Download models from: https://alphacephei.com/vosk/models\n"
                f"Extract to: models/audio/vosk/"
            )

        self._model = Model(model_path)
        self._recognizer = KaldiRecognizer(self._model, 16000)
        self._stop_event = threading.Event()

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

    def listen_and_transcribe(self, duration_seconds: int = 0) -> str:
        """
        Listen to microphone input and transcribe speech to text

        Args:
            duration_seconds: Duration to listen in seconds. 0 means listen until something is detected.
        """
        # Reset the stop event before starting
        self._stop_event.clear()

        stream: pyaudio.Stream = self._open_microphone_stream()
        stream.start_stream()
        start_time = os.times()[4]

        logger.info("Listening for speech...")
        result = ""

        try:
            while not self._stop_event.is_set():
                # Check time conditions
                elapsed_time = os.times()[4] - start_time
                if duration_seconds > 0 and elapsed_time >= duration_seconds:
                    break

                # Stop when we get a result
                if result != "":
                    break

                data = stream.read(4096, exception_on_overflow=False)
                if len(data) == 0:
                    break

                if self._recognizer.AcceptWaveform(data):
                    parsed_result = json.loads(self._recognizer.Result())
                    result = parsed_result.get("text", "")

        finally:
            stream.stop_stream()
            stream.close()

        return result

    def stop_listening(self):
        """Stop the current listening operation"""
        self._stop_event.set()


def main():
    """Example usage"""

    try:
        stt = VoskSpeechToTextHelper("vosk-model-small-en-us-0.15")
        text = stt.listen_and_transcribe(duration_seconds=0)
        logger.info(f"Transcribed Text: {text}")
    except FileNotFoundError as e:
        logger.error(e)


if __name__ == "__main__":
    main()
