"""
Voice capture endpoint — POST /api/voice/transcribe
Accepts WebM/OGG audio from browser MediaRecorder, returns transcribed text
via faster-whisper (CTranslate2 backend, runs on CPU/NPU).
"""

from __future__ import annotations
import io
import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

log = logging.getLogger("mc.voice")

router = APIRouter(prefix="/api/voice")

_whisper_model = None
_MODEL_SIZE = os.environ.get("MC_WHISPER_MODEL", "tiny")
_MODEL_DIR = Path(__file__).parent.parent.parent.parent / ".whisper_cache"


def _get_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    try:
        from faster_whisper import WhisperModel
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)
        log.info("Loading Whisper %s model (first run downloads ~75MB)…", _MODEL_SIZE)
        _whisper_model = WhisperModel(
            _MODEL_SIZE,
            device="cpu",
            compute_type="int8",
            download_root=str(_MODEL_DIR),
        )
        log.info("Whisper model loaded")
        return _whisper_model
    except Exception as exc:
        log.error("Failed to load Whisper: %s", exc)
        raise


@router.get("/status")
async def voice_status():
    """Return whether the Whisper model is loaded and ready."""
    try:
        from faster_whisper import WhisperModel  # noqa: F401 — just check import
        loaded = _whisper_model is not None
        return {"available": True, "loaded": loaded, "model": _MODEL_SIZE}
    except ImportError:
        return {"available": False, "loaded": False, "model": None}


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """
    Receive audio blob (webm/ogg/wav) from browser, transcribe via Whisper.
    Returns {"text": "transcribed text", "language": "ko"}.
    """
    try:
        model = _get_model()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Whisper unavailable: {exc}")

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Write to temp file — faster-whisper needs a file path
    suffix = ".webm"
    ct = audio.content_type or ""
    if "ogg" in ct:
        suffix = ".ogg"
    elif "wav" in ct:
        suffix = ".wav"
    elif "mp4" in ct or "m4a" in ct:
        suffix = ".mp4"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        segments, info = model.transcribe(
            tmp_path,
            language=None,       # auto-detect (Korean/English/etc.)
            beam_size=1,         # fast mode
            vad_filter=True,     # skip silence
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return JSONResponse({"text": text, "language": info.language})
    except Exception as exc:
        log.exception("Transcription error")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
