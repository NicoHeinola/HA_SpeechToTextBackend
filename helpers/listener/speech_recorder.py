"""Speech recorder helper.

Opens the microphone stream and records until speech is detected and ends.
Provides a small, testable class that encapsulates stream management and energy-based
speech detection.
"""

from __future__ import annotations

import os
import time
import audioop
from typing import Optional

import pyaudio


class SpeechRecorder:
    def __init__(
        self,
        rate: int = 16000,
        channels: int = 1,
        format: int = pyaudio.paInt16,
        frames_per_buffer: int = 8192,
    ):
        self._rate = rate
        self._channels = channels
        self._format = format
        self._frames_per_buffer = frames_per_buffer

        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None

    def _open_stream(self) -> pyaudio.Stream:
        if self._stream is not None:
            return self._stream

        # Suppress ALSA / device warnings during PyAudio instantiation
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr_fd = os.dup(2)
        os.dup2(devnull, 2)
        try:
            self._pyaudio = pyaudio.PyAudio()
            self._stream = self._pyaudio.open(
                format=self._format,
                channels=self._channels,
                rate=self._rate,
                input=True,
                frames_per_buffer=self._frames_per_buffer,
            )
            self._stream.start_stream()
        finally:
            os.dup2(old_stderr_fd, 2)
            os.close(devnull)
            os.close(old_stderr_fd)

        return self._stream

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None

    def record_until_speech_end(
        self,
        duration_seconds: int,
        start_threshold: int = 500,
        silence_threshold: int = 400,
        silence_max_frames: int = 3,
        chunk: int = 4096,
    ) -> bytes:
        """Open the stream (if needed) and record until speech end.

        Returns raw PCM bytes (16-bit mono) — may be empty if nothing detected.
        """
        stream = self._open_stream()

        start_time = time.time()
        buffer = bytearray()

        speech_started = False
        silence_frames = 0

        while self._stream is not None:
            # duration guard
            if duration_seconds > 0 and (time.time() - start_time) >= duration_seconds:
                break

            try:
                chunk_bytes = stream.read(chunk, exception_on_overflow=False)
            except Exception:
                break

            if not chunk_bytes:
                break

            try:
                rms = audioop.rms(chunk_bytes, 2)
            except Exception:
                rms = 0

            if not speech_started:
                if rms >= start_threshold:
                    speech_started = True
                    buffer.extend(chunk_bytes)
                    silence_frames = 0
                else:
                    continue
            else:
                buffer.extend(chunk_bytes)

                if rms < silence_threshold:
                    silence_frames += 1
                else:
                    silence_frames = 0

                if silence_frames >= silence_max_frames:
                    break

        return bytes(buffer)
