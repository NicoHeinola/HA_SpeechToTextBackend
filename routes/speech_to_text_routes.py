from fastapi import APIRouter, Body
from helpers.listener.microphone_listener import MicrophoneListener
from middleware.auth import require_auth


router = APIRouter()

# Global state for tracking listening status
microphone_listener: MicrophoneListener = MicrophoneListener()


@router.post("/start-listening")
def start_listening(token: str = require_auth(), body: dict = Body(...)):
    """
    Start listening for speech input.
    Requires valid API token authentication.
    """
    global microphone_listener
    if microphone_listener.is_listening:
        return {"status": "already_listening", "is_listening": True}

    model: str = body.get("model", "vosk-model-small-en-us-0.15")
    duration_seconds: int | None = int(body.get("duration_seconds", 10))

    microphone_listener.start_listening(model=model, duration_seconds=duration_seconds)

    return {"status": "listening", "is_listening": True}


@router.post("/stop-listening")
def stop_listening(token: str = require_auth()):
    """
    Stop listening for speech input.
    Requires valid API token authentication.
    """
    global microphone_listener
    if not microphone_listener.is_listening:
        return {"status": "not_listening", "is_listening": False}

    microphone_listener.stop_listening()

    return {"status": "stopped", "is_listening": False}


@router.get("/is-listening")
def is_listening(token: str = require_auth()):
    """
    Check if the system is currently listening for speech input.
    Requires valid API token authentication.
    """
    return {"is_listening": microphone_listener.is_listening}
