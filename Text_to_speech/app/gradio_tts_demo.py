"""Gradio demo of the TTS engine - run this for the team / Design Day demo.

    python app/gradio_tts_demo.py        (or double-click run_demo.bat on Windows)

Paste any chatbot answer (or pick an example), press Speak. The answer is
fed to the engine word-by-word like a streaming LLM, spoken on this
computer's speakers as each phrase is ready, and the table shows how the
answer was cut into phrases, which voice spoke each one, and how fast.
"""

from __future__ import annotations

import os
import re
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import gradio as gr           # noqa: E402
import numpy as np            # noqa: E402

from evaluation.latency_metrics import summarize          # noqa: E402
from voice.audio import SAMPLE_RATE                       # noqa: E402
from voice.playback import LocalPlayer                    # noqa: E402
from voice.tts import TTSEngine, TTSError                 # noqa: E402

ENGINE = TTSEngine()
ENGINE.warm_up()
PLAYER_OK, PLAYER_INFO = LocalPlayer.available()
_current = {"player": None}
NAME = ENGINE.settings["principal_name"]

MODES = {
    "Auto - ElevenLabs, offline backup": "auto",
    "ElevenLabs only": "elevenlabs",
    "Offline voice only (no internet)": "offline",
}
HEADERS = ["#", "Phrase sent to the voice", "Voice engine", "First audio (ms)",
           "Audio (s)", "From cache"]

EXAMPLES = [
    [f"Oh, the summer of 1974! Your grandmother and I drove all the way to Halifax in that old "
     f"blue Volkswagen. It broke down twice, and we laughed the whole way there."],
    ["I'm sorry, that isn't something I recorded in my memories, so I can't tell you about it. "
     "Your mother might remember. Why don't you ask her?"],
    ["**My advice?** Work hard, but never miss Sunday dinner with your family [2]. "
     "Dr. Patel, our neighbour on Elm St. in Ottawa, used to say the very same thing."],
]


def simulate_llm_stream(text: str, delay_s: float = 0.025):
    """Release the text word by word (~40 tokens/s), like a streaming LLM."""
    for tok in re.findall(r"\S+\s*", text):
        time.sleep(delay_s)
        yield tok


def status_md() -> str:
    st = ENGINE.status()
    lines = ["**Voice engines**"]
    labels = {"elevenlabs": "ElevenLabs (cloud)", "system": "Offline backup voice"}
    for name, b in st["backends"].items():
        mark = "OK" if b["available"] else "not available"
        extra = f" - retry in {b['cooling_down_s']:.0f} s" if b["cooling_down_s"] else ""
        lines.append(f"- {labels.get(name, name)}: **{mark}** ({b['detail']}){extra}")
    lines.append(f"- Speakers: {'**OK** (' + PLAYER_INFO + ')' if PLAYER_OK else PLAYER_INFO}")
    lines.append(f"- Cached phrases: {st['cache_entries']}")
    return "\n".join(lines)


def metrics_md(m, live_note: str = "") -> str:
    if m is None:
        return live_note or "Press **Speak** to start."
    target = ENGINE.settings["metrics"]["first_audio_target_ms"]
    fa = m.first_audio_ms
    verdict = "" if fa is None else (" - meets the < 500 ms target" if fa < target
                                     else " - above the 500 ms target")
    out = [f"**Turn {m.turn_id}** - voice engine(s): {', '.join(m.backends) or '-'}",
           f"- First audio: **{fa} ms**{verdict}",
           f"- First text received -> first audio: {m.text_to_audio_ms} ms",
           f"- Audio length: {m.audio_s:.2f} s, total time (incl. waiting for text): "
           f"{m.total_ms} ms, real-time factor: {m.rtf if m.rtf is not None else 'n/a (all from cache)'}"]
    if m.cancelled:
        out.append("- **Interrupted** - remaining audio was discarded.")
    for n in m.warnings + m.fallbacks + m.errors:
        out.append(f"- Note: {n}")
    return "\n".join(out)


def phrase_rows(m):
    return [[p.index, p.text, p.backend, p.first_audio_ms, p.audio_s, "yes" if p.cache_hit else ""]
            for p in m.phrases]


def speak(text, voice, mode_label, simulate, use_speakers, session_id):
    if not text or not text.strip():
        yield [], "Type or pick some text first.", None, status_md()
        return
    mode = MODES[mode_label]
    stream = simulate_llm_stream(text) if simulate else text
    player = None
    if use_speakers and PLAYER_OK:
        player = LocalPlayer()
        player.start()
        _current["player"] = player
    live_rows, pcm_parts = [], []
    try:
        for chunk in ENGINE.synthesize_speech(stream, voice=voice, mode=mode,
                                              session_id=session_id):
            if chunk.pcm:
                pcm_parts.append(chunk.pcm)
                if player:
                    player.feed(chunk.pcm)
            if chunk.is_phrase_end:
                live_rows.append([chunk.phrase_index, chunk.text, chunk.backend, None,
                                  round(chunk.start_s, 2), ""])
                yield live_rows, "Speaking...", None, status_md()
    except TTSError as e:
        if player:
            player.stop()
        yield live_rows, f"**Could not speak:** {e}", None, status_md()
        return
    m = ENGINE.last_metrics
    yield phrase_rows(m), metrics_md(m), None, status_md()
    audio = (SAMPLE_RATE, np.frombuffer(b"".join(pcm_parts), dtype="<i2")) if pcm_parts else None
    if player:
        if m.cancelled:
            player.stop()
        else:
            player.finish(timeout=120)
        note = f"\n- Speaker playback: first sound {player.first_sound_latency_ms} ms after " \
               f"audio arrived, {player.underruns} buffer underrun(s)"
        yield phrase_rows(m), metrics_md(m) + note, gr.update(value=audio, autoplay=False), status_md()
    else:
        yield phrase_rows(m), metrics_md(m), gr.update(value=audio, autoplay=True), status_md()


def stop():
    ENGINE.interrupt()
    p = _current.get("player")
    if p:
        p.stop()
    return "Stopped - the rest of the answer was cancelled."


def latency_report():
    target = ENGINE.settings["metrics"]["first_audio_target_ms"]
    rows = summarize(ENGINE.metrics_log.load() if ENGINE.metrics_log else [], target)
    if not rows:
        return "No measurements yet. Speak a few answers first (cache hits are not counted)."
    out = [f"First-audio latency from `logs/tts_metrics.jsonl` (target < {target} ms)\n",
           "| Voice engine | Turns | P50 (ms) | P95 (ms) | P50 meets target | P95 meets target | RTF (P50) |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['backend']} | {r['turns']} | {r['first_audio_p50_ms']} | "
                   f"{r['first_audio_p95_ms']} | {'yes' if r['p50_meets_target'] else 'no'} | "
                   f"{'yes' if r['p95_meets_target'] else 'no'} | {r['rtf_p50']} |")
    return "\n".join(out)


TEAM_SNIPPET = f'''
```python
import sys; sys.path.insert(0, "TTS Engine/src")      # or: pip install -e "TTS Engine"
from voice import synthesize_speech, speak, interrupt

# 1. Simplest: say the chatbot's answer out loud on this computer
speak(answer_text)

# 2. Streaming: pass the LLM token stream straight in, get audio chunks out
for chunk in synthesize_speech(llm_token_stream, session_id=visitor_id):
    player_or_avatar.feed(chunk.pcm)   # int16 mono PCM, {SAMPLE_RATE} Hz
    # chunk.start_s = position of this audio in the answer (for lip-sync)

# 3. Gradio: a complete clip for gr.Audio
from voice import get_engine
sr, samples = get_engine().synthesize_to_numpy(answer_text)

# 4. Visitor asked something new / pressed Stop
interrupt()
```
HTTP alternative (any language, e.g. the AR web page): run
`uvicorn api:app --app-dir app --port 8001`, then `POST /tts` with JSON `{{"text": "..."}}`
returns a WAV; `POST /tts/stream` streams it.
'''


with gr.Blocks(title="AI Ancestor Interaction - Voice (TTS)") as demo:
    session = gr.State(lambda: uuid.uuid4().hex)
    gr.Markdown(f"## AI Ancestor Interaction - Voice engine (text-to-speech)\n"
                f"> **AI representation notice:** this voice is generated by AI from memories "
                f"{NAME} recorded and approved. It is not {NAME}.")
    with gr.Tab("Speak"):
        with gr.Row():
            with gr.Column(scale=3):
                text = gr.Textbox(label="Text from the chatbot (RAG answer)", lines=5,
                                  placeholder="Paste an answer from the chatbot...")
                #gr.Examples(EXAMPLES, inputs=[text], label="Example answers")
                with gr.Row():
                    voice = gr.Dropdown(ENGINE.registry.choices(), value=ENGINE.registry.default_key,
                                        label="Voice")
                    mode = gr.Radio(list(MODES), value=next(k for k, v in MODES.items()
                                                             if v == ENGINE.settings["mode"]),
                                    label="Voice engine")
                with gr.Row():
                    simulate = gr.Checkbox(True, label="Feed the text word-by-word like a streaming LLM")
                    speakers = gr.Checkbox(PLAYER_OK, label="Play on this computer's speakers while streaming",
                                           interactive=PLAYER_OK)
                with gr.Row():
                    speak_btn = gr.Button("Speak", variant="primary")
                    stop_btn = gr.Button("Stop")
                    new_session = gr.Button("New visitor (repeat AI notice)")
            with gr.Column(scale=2):
                status = gr.Markdown(status_md())
                metrics = gr.Markdown("Press **Speak** to start.")
        table = gr.Dataframe(headers=HEADERS, interactive=False, wrap=True,
                             column_widths=["5%", "52%", "15%", "11%", "9%", "8%"],
                             label="How the answer was spoken, phrase by phrase")
        audio = gr.Audio(label="Whole answer (browser playback / download)", type="numpy",
                         interactive=False)
    with gr.Tab("Latency report"):
        report = gr.Markdown(latency_report())
        gr.Button("Refresh").click(latency_report, outputs=report)
    with gr.Tab("For teammates"):
        gr.Markdown(TEAM_SNIPPET)

    speak_btn.click(speak, inputs=[text, voice, mode, simulate, speakers, session],
                    outputs=[table, metrics, audio, status])
    stop_btn.click(stop, outputs=metrics)
    new_session.click(lambda: (uuid.uuid4().hex, "New visitor session - the AI notice will be "
                               "spoken before the next answer."), outputs=[session, metrics])


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2)
    demo.launch(server_name="127.0.0.1", server_port=int(os.environ.get("TTS_DEMO_PORT", 7860)),
                inbrowser=True)
