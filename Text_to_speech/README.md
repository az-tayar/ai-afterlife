# TTS Engine — AI Ancestor Interaction (GNG5140, Team 4)

The **text-to-speech (speech synthesis) part** of the team pipeline. It takes the chatbot's
answer — a whole string or the LLM's token stream — and speaks it in phrases as soon as
each phrase is ready. It follows the team blueprint (*AI_afterlife.pdf*, Phase 3):

| Team decision (blueprint / client) | How this engine meets it |
|---|---|
| TTS provider: **ElevenLabs** | Primary voice, streaming endpoint, `eleven_flash_v2_5` low-latency model |
| "Stream LLM text into TTS in natural phrase chunks" | `PhraseChunker`: first phrase released early, later phrases are whole sentences |
| "Stream synthesized audio to playback" | Audio arrives in ~46 ms pieces; `LocalPlayer` plays while the rest is generated |
| "Allow user interruptions and cancel stale audio" | A new question cancels the old answer; **Stop** silences instantly |
| "Record timing metrics for every stage"; TTS first audio **< 500 ms**, P50/P95 | Every turn logged to `logs/tts_metrics.jsonl`; `scripts/benchmark_tts.py` prints P50/P95 |
| Interface `synthesize_speech(text_stream)` in `src/voice/tts.py` | Exactly that name and location |
| Python + Gradio + pytest; FastAPI when services split | Gradio demo, optional FastAPI service, 37 pytest tests |
| Modular, replaceable providers | Backends behind one `TTSBackend` interface |
| Consent; make AI identity explicit (client, blueprint) | Cloned voice refused without a consent record; written AI notice always on screen (spoken notice optional, off by default) |
| Network failure must not leave silence (test plan T9) | Offline backup voice takes over; cloud retried after 10 s |
| Budget $100–$200 | ElevenLabs free tier + phrase cache; offline voice costs nothing |

## 1. Run the demo (Windows)

1. Install **Python 3.10 or newer** from python.org (tick *Add Python to PATH*).
2. Double-click **`run_demo.bat`**. The first run installs packages (a few minutes);
   then the demo opens in your browser at http://127.0.0.1:7860.
3. Paste an answer into the text box and press **Speak**.

It works straight away with the **offline backup voice** (Windows' built-in SAPI voice; the panel shows
"sapi5").
To use the ElevenLabs voice, open `.env` (created on first run) and paste your key:

```
ELEVENLABS_API_KEY=sk_...your key...
```

Get a key at elevenlabs.io → Profile → API Keys (the free plan works). Restart the demo; the
right-hand panel then shows *ElevenLabs (cloud): OK*.

Manual start instead of the .bat file:
```
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app\gradio_tts_demo.py
```

## 2. Two-minute demonstration script

Paste any multi-sentence answer into the text box first, for example:
*"Oh, the summer of 1974! Your grandmother and I drove all the way to Halifax in that old blue
Volkswagen. It broke down twice, and we laughed the whole way there."*

1. **Normal answer** — *Auto* mode, *Speak*. Point out: speech starts before the whole answer
   exists, and the phrase table and first-audio time are shown on the right (target < 500 ms;
   measured on the demo laptop: about 175 ms once connected).
2. **Clean reading** — add `**bold**` markers and a citation like `[2]`, and write "Dr." or "St."
   mid-sentence. The markers and citation are not read aloud, and the abbreviations do not break
   the sentence.
3. **Interruption** — paste a long answer, *Speak*, then *Stop* after a second. The voice stops at
   once and the panel says *Interrupted*.
4. **Network failure** — turn Wi-Fi off and press *Speak* again. The backup voice answers and
   the panel notes why; turn Wi-Fi back on and ElevenLabs is used again within 10 seconds.
5. **Latency report** tab — P50/P95 first-audio times from everything spoken so far.

Tip: the first ElevenLabs answer after starting the demo is slower (it opens the connection),
so speak one answer before the judges arrive.

## 3. Using it from the team's code

```python
import sys; sys.path.insert(0, "TTS Engine/src")   # or: pip install -e "TTS Engine"
from voice import synthesize_speech, speak, interrupt, get_engine

speak(answer_text)                                   # say it on this computer's speakers

for chunk in synthesize_speech(llm_token_stream, session_id=visitor_id):
    avatar.feed(chunk.pcm)        # int16 mono PCM, 22 050 Hz
    # chunk.start_s = where this audio sits in the answer (for lip-sync)

sr, samples = get_engine().synthesize_to_numpy(answer_text)   # for gr.Audio
interrupt()                                          # visitor asked something new / pressed Stop
```

Over HTTP (any language — e.g. the AR web page on the iPad):
```
uvicorn api:app --app-dir app --port 8001
POST /tts          {"text": "..."}  -> audio/wav
POST /tts/stream   {"text": "..."}  -> WAV streamed while it is generated
POST /tts/interrupt
GET  /health
```

Command line: `python -m voice "Hello there"` (run with `src` on `PYTHONPATH`, or after
`pip install -e .`), `--out file.wav`, `--mode offline`, `--check`.

## 4. Testing and measurement

```
python -m pytest -q                                      # 37 tests, <10 s, no key needed
python scripts\benchmark_tts.py --mode elevenlabs --runs 5   # needs the key
python scripts\benchmark_tts.py --mode offline --runs 5
```
The benchmark prints P50/P95 first-audio latency against the 500 ms target and saves a CSV in
`results/` for the Deliverable D/E test tables. ElevenLabs behaviour (normal streaming, bad
key, exhausted credits, timeout, dropped connection) is tested against a local mock server, so
the tests never spend credits.

## 5. Settings

`configs/settings.yaml` — mode, ElevenLabs model and timeouts, voice speed, chunking limits,
retry delay, cache, latency targets, and the spoken AI notice (`disclosure.enabled`, off in this
version; set it to `true` to have the notice spoken at the start of each visitor session).
`configs/voices.yaml` — voices. A `cloned` voice is used **only** if `consent.granted: true`
and `consent.record_id` is filled in; otherwise the default stock voice is used and a
warning is shown.

## 6. Folder map

```
src/voice/tts.py               engine: turn control, fallback, cancellation, metrics
src/voice/text_chunker.py      text clean-up and phrase splitting
src/voice/backends/            elevenlabs_backend.py, system_backend.py (offline; SAPI5 on Windows), base.py
src/voice/playback.py          streaming speaker output, Stop, playback clock
src/voice/cache.py             phrase cache          src/voice/voice_registry.py  voices + consent
src/voice/audio.py             PCM/WAV helpers       src/voice/config.py          settings loader
src/evaluation/latency_metrics.py   timing records, P50/P95
app/gradio_tts_demo.py         demo UI              app/api.py   HTTP service
scripts/benchmark_tts.py       latency benchmark    tests/       pytest suite + mock ElevenLabs
docs/                          System Architecture and Theory of Operation
```

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| "ElevenLabs: not available (no ELEVENLABS_API_KEY set)" | Put the key in `.env`, restart |
| "ElevenLabs 401" | Key wrong or revoked — create a new key |
| "ElevenLabs 429" | Free credits used up or too many requests — wait, or use *Offline* mode |
| No sound but the table fills | Tick *Play on this computer's speakers*, check Windows volume/output device, or use the browser player under the table |
| "Speakers: no speaker output" | No audio device found by PortAudio; use the browser player |
| Offline voice speaks only the first sentence | An old copy is running: the panel must say "sapi5". Close every demo window and start `run_demo.bat` again |
| `run_demo.bat` closes with an error | Install Python 3.10+ with *Add to PATH*, then delete `.venv` and run again |

The ElevenLabs key lives only in `.env`, which is git-ignored — never paste it into code or
`settings.yaml`. All testing uses the fictional Principal "Walter"; no real family data.
