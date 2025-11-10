import logging
import threading

from helpers.speech_to_text.vosk_speech_to_text_helper import VoskSpeechToTextHelper


logger = logging.getLogger(__name__)


class MicrophoneListener:
    def __init__(self):
        self._is_listening = False
        self._listening_thread: threading.Thread | None = None
        self._speech_to_text_helper: VoskSpeechToTextHelper | None = None

    @property
    def is_listening(self) -> bool:
        return self._is_listening and self._listening_thread is not None and self._listening_thread.is_alive()

    def _listen_loop(self, model: str, duration_seconds: int):
        self._speech_to_text_helper = VoskSpeechToTextHelper(model)
        text: str = self._speech_to_text_helper.listen_and_transcribe(duration_seconds=duration_seconds)

        logger.info(f"Transcribed text: {text}")

        # Automatically restart listening if duration is zero (continuous mode) and still listening
        if duration_seconds == 0 and self._is_listening:
            self._is_listening = False
            self._listening_thread = None
            self._speech_to_text_helper = None

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
