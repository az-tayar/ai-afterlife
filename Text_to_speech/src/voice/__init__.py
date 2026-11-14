"""Voice package for the AI Ancestor Interaction project (Team 4, GNG5140).

Quick use:
    from voice import synthesize_speech, speak
    speak("Hello, I remember that summer very well.")
    for chunk in synthesize_speech(llm_token_stream):
        send_to_player(chunk.pcm)
"""

from .audio import SAMPLE_RATE, AudioChunk
from .tts import TTSEngine, TTSError, get_engine, interrupt, speak, synthesize_speech

__all__ = ["SAMPLE_RATE", "AudioChunk", "TTSEngine", "TTSError", "get_engine",
           "interrupt", "speak", "synthesize_speech"]
__version__ = "1.0.0"
