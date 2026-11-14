"""Small HTTP service around the TTS engine (blueprint: FastAPI "when separating UI and services").

Lets parts of the system written in other languages - for example the AR web
page that runs on the iPad - ask for speech over the network.

    uvicorn api:app --app-dir app --port 8001

    GET  /health          engine and backend status
    POST /tts             {"text": "...", "voice": null, "mode": null, "session_id": null}
                          -> complete answer as audio/wav
    POST /tts/stream      same body -> WAV streamed while it is being generated
    POST /tts/interrupt   stop the answer currently being spoken
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi import FastAPI, HTTPException                 # noqa: E402
from fastapi.responses import Response, StreamingResponse  # noqa: E402
from pydantic import BaseModel, Field                      # noqa: E402

from voice.audio import SAMPLE_RATE, streaming_wav_header, wav_bytes  # noqa: E402
from voice.tts import TTSEngine, TTSError                  # noqa: E402

app = FastAPI(title="Team 4 TTS service", version="1.0.0")
_engine: Optional[TTSEngine] = None


def engine() -> TTSEngine:
    global _engine
    if _engine is None:
        _engine = TTSEngine()
    return _engine


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: Optional[str] = None
    mode: Optional[str] = None
    session_id: Optional[str] = None


def _check_mode(mode):
    if mode not in (None, "auto", "elevenlabs", "offline"):
        raise HTTPException(422, "mode must be auto, elevenlabs or offline")


@app.get("/health")
def health():
    return engine().status()


@app.post("/tts")
def tts(req: TTSRequest):
    _check_mode(req.mode)
    try:
        pcm = engine().synthesize(req.text, voice=req.voice, mode=req.mode,
                                  session_id=req.session_id)
    except TTSError as e:
        raise HTTPException(503, str(e))
    m = engine().last_metrics
    return Response(wav_bytes(pcm, SAMPLE_RATE), media_type="audio/wav", headers={
        "X-TTS-Backends": ",".join(m.backends),
        "X-TTS-First-Audio-Ms": str(m.first_audio_ms)})


@app.post("/tts/stream")
def tts_stream(req: TTSRequest):
    _check_mode(req.mode)

    def gen():
        yield streaming_wav_header(SAMPLE_RATE)
        try:
            for chunk in engine().synthesize_speech(req.text, voice=req.voice, mode=req.mode,
                                                    session_id=req.session_id):
                if chunk.pcm:
                    yield chunk.pcm
        except TTSError:
            return
    return StreamingResponse(gen(), media_type="audio/wav")


@app.post("/tts/interrupt")
def tts_interrupt():
    return {"interrupted": engine().interrupt()}
