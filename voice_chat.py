"""
Voice chat for the memory companion.

    microphone -> Deepgram streaming STT -> RAG -> streaming LLM -> TTS -> speakers

* You speak; Deepgram detects when you stop (endpointing) and returns the text.
* The answer is spoken while it is still being written (team TTS engine).
* BARGE-IN: the microphone keeps listening while the answer plays. If you start
  talking, the speech and the rest of the answer are cancelled at once and your new
  question is taken.

Use HEADPHONES for barge-in. On laptop speakers the microphone can hear the
assistant itself; the code filters most of that, but headphones are reliable.
On laptop speakers it is switched off automatically (the mic is muted while the
assistant talks). Force it with --barge-in, or off with --no-barge-in.

Run:
    python voice_chat.py --path sample_principal_interview.pdf
    python voice_chat.py --path sample_principal_interview.pdf --debug
    python voice_chat.py --list-devices            # find your microphone number
Needs in .env: OPENAI_API_KEY, PINECONE_API_KEY, DEEPGRAM_API_KEY (and ELEVENLABS_API_KEY for the best voice)
Say "goodbye" or press Ctrl+C to quit.
"""
import argparse
import asyncio
import json
import os
import queue
import re
import sys
import threading
import time
from difflib import SequenceMatcher
from urllib.parse import urlencode

from dotenv import find_dotenv, load_dotenv

try:
    import rag_optimized as rag
except ImportError:  # you renamed the file
    import rag_query_engine as rag

DG_URL = "wss://api.deepgram.com/v1/listen"
MIC_RATE = 16000

QUIT_PHRASES = {"goodbye", "good bye", "bye", "quit", "exit", "stop listening"}
INTERRUPT_WORDS = {"stop", "wait", "pause", "enough", "hold"}
_WORD = re.compile(r"[a-z0-9']+")


# ======================================================
# ECHO / BARGE-IN HELPERS
# ======================================================

def words(text):
    return _WORD.findall(text.lower())


def _heard_in(word, vocab):
    """Exact or near match (speech-to-text often spells names slightly differently)."""
    if word in vocab:
        return True
    return any(abs(len(v) - len(word)) <= 2 and SequenceMatcher(None, word, v).ratio() >= 0.8
               for v in vocab)


def is_echo(text, spoken):
    """True if (almost) all words of `text` were just spoken by the assistant."""
    w, vocab = words(text), set(words(spoken))
    if not w or not vocab:
        return False
    return sum(_heard_in(x, vocab) for x in w) / len(w) >= 0.7


def is_barge_in(text, spoken):
    """The user is really talking over the assistant (not the assistant's own echo)."""
    w = words(text)
    if not w or is_echo(text, spoken):
        return False
    return len(w) >= 3 or any(x in INTERRUPT_WORDS for x in w[:2])


def output_is_speakers():
    """True when sound goes to laptop speakers (the mic will hear the assistant)."""
    try:
        import sounddevice as sd
        name = sd.query_devices(kind="output")["name"].lower()
        return "speaker" in name and "headphone" not in name
    except Exception:
        return False


# ======================================================
# DEEPGRAM STREAMING STT
# ======================================================

class DeepgramSTT:
    """Streams the microphone to Deepgram and returns finished utterances.

    - next_utterance(): blocks until the user has finished a sentence.
    - set_activity_callback(fn): fn(partial_text) is called while the user is speaking
      (used for barge-in). It runs on the STT thread, so keep it quick.
    - muted=True sends silence instead of the mic (half-duplex mode).
    """

    def __init__(self, api_key, language="en", model="nova-3", endpoint_ms=400,
                 utterance_end_ms=1200, device=None):
        self.api_key, self.language, self.model = api_key, language, model
        self.endpoint_ms, self.utterance_end_ms, self.device = endpoint_ms, utterance_end_ms, device
        self.muted = False
        self.echo_ref = None          # (callable returning spoken text, valid-until timestamp)
        self.error = None
        self._utterances = queue.Queue()
        self._callback = None
        self._buffer, self._interim = [], ""
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread = None

    # ---------- public ----------
    def start(self):
        self._thread = threading.Thread(target=lambda: asyncio.run(self._main()),
                                        daemon=True, name="deepgram-stt")
        self._thread.start()
        self._ready.wait(15)
        if self.error:
            hint = " (check DEEPGRAM_API_KEY)" if "401" in self.error or "403" in self.error else ""
            raise RuntimeError(self.error + hint)

    def close(self):
        self._stop.set()

    def set_activity_callback(self, fn):
        self._callback = fn

    def next_utterance(self, timeout=None):
        return self._utterances.get(timeout=timeout)

    def drain(self):
        while not self._utterances.empty():
            try:
                self._utterances.get_nowait()
            except queue.Empty:
                break

    # ---------- microphone ----------
    def _open_mic(self, push):
        import sounddevice as sd

        def on_audio(indata, frames, t, status):
            data = bytes(indata)
            if self.muted:
                data = bytes(len(data))   # silence keeps the connection alive
            push(data)

        stream = sd.RawInputStream(samplerate=MIC_RATE, channels=1, dtype="int16",
                                   blocksize=1600, device=self.device, callback=on_audio)
        stream.start()
        return stream

    # ---------- websocket ----------
    async def _main(self):
        import websockets
        loop = asyncio.get_running_loop()
        audio_q = asyncio.Queue(maxsize=200)

        def put(b):
            try:
                audio_q.put_nowait(b)
            except asyncio.QueueFull:
                pass

        def push(b):
            loop.call_soon_threadsafe(put, b)

        try:
            mic = self._open_mic(push)
        except Exception as e:
            self.error = f"Microphone error: {e}"
            self._ready.set()
            return

        params = urlencode({
            "model": self.model, "language": self.language,
            "encoding": "linear16", "sample_rate": MIC_RATE, "channels": 1,
            "interim_results": "true", "endpointing": self.endpoint_ms,
            "utterance_end_ms": self.utterance_end_ms, "vad_events": "true",
            "smart_format": "true", "punctuate": "true",
        })
        url = f"{DG_URL}?{params}"
        headers = {"Authorization": f"Token {self.api_key}"}
        backoff, connected_once = 1, False
        try:
            while not self._stop.is_set():
                try:
                    async with websockets.connect(url, additional_headers=headers,
                                                  max_size=None) as ws:
                        self.error, backoff, connected_once = None, 1, True
                        self._ready.set()
                        sender = asyncio.create_task(self._send(ws, audio_q))
                        try:
                            await self._receive(ws)
                        finally:
                            sender.cancel()
                except TypeError as e:
                    self.error = f"{e} - run: pip install -U 'websockets>=14'"
                    self._ready.set()
                    return
                except Exception as e:
                    self.error = f"{e.__class__.__name__}: {e}"
                    self._ready.set()
                    if connected_once:
                        print(f"\n[stt] connection lost ({self.error}); reconnecting...")
                    elif "401" in self.error or "403" in self.error:
                        return  # bad key: do not retry forever
                if self._stop.is_set():
                    break
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 8)
        finally:
            try:
                mic.stop()
                mic.close()
            except Exception:
                pass

    async def _send(self, ws, audio_q):
        try:
            while True:
                await ws.send(await audio_q.get())
        except Exception:
            pass  # connection closed; _receive ends too and we reconnect

    async def _receive(self, ws):
        async for raw in ws:
            if isinstance(raw, bytes):
                continue
            msg = json.loads(raw)
            kind = msg.get("type")
            if kind == "Results":
                self._on_results(msg)
            elif kind == "UtteranceEnd":
                self._finish_utterance()

    # ---------- results ----------
    def _is_echo_piece(self, text):
        ref = self.echo_ref
        if not ref:
            return False
        spoken, until = ref
        return time.time() < until and len(words(text)) >= 2 and is_echo(text, spoken())

    def _on_results(self, msg):
        alts = (msg.get("channel") or {}).get("alternatives") or [{}]
        text = (alts[0].get("transcript") or "").strip()
        if msg.get("is_final"):
            if text and not self._is_echo_piece(text):
                self._buffer.append(text)
            self._interim = ""
            if msg.get("speech_final"):
                self._finish_utterance()
                return
        else:
            self._interim = "" if self._is_echo_piece(text) else text
        current = " ".join(self._buffer + ([self._interim] if self._interim else []))
        cb = self._callback
        if current and cb:
            cb(current)

    def _finish_utterance(self):
        text = " ".join(self._buffer).strip()
        self._buffer, self._interim = [], ""
        if text:
            self._utterances.put(text)


# ======================================================
# VOICE LOOP
# ======================================================

def voice_loop(companion, stt, speaker, barge_in=True):
    last_answer = ""
    print("\nListening. Speak your question. Say 'goodbye' to quit.\n")
    while True:
        text = stt.next_utterance()
        if len(words(text)) >= 3 and is_echo(text, last_answer) and time.time() < _echo_until["t"]:
            continue  # the mic heard the assistant's own voice
        if " ".join(words(text)) in QUIT_PHRASES:
            print("Goodbye!")
            return
        print(f"\nYou: {text}")

        stop = threading.Event()
        stt.echo_ref = (lambda: companion.answer_buffer, float("inf"))
        if barge_in:
            def on_speech(partial, stop=stop):
                if not stop.is_set() and is_barge_in(partial, companion.answer_buffer):
                    stop.set()
                    print(f"\n[barge-in] heard: '{partial}'")
                    if speaker:
                        speaker.stop()
            stt.set_activity_callback(on_speech)
        else:
            stt.muted = True   # half-duplex: do not listen while the assistant talks
        try:
            companion.ask(text, stop=stop)
        except KeyboardInterrupt:
            stop.set()
            if speaker:
                speaker.stop()
        finally:
            stt.set_activity_callback(None)
            stt.muted = False
            last_answer = companion.answer_buffer
            _echo_until["t"] = time.time() + 1.5
            stt.echo_ref = (lambda: last_answer, time.time() + 1.5)
        print("\n[interrupted] Listening..." if stop.is_set() else "\nListening...")


_echo_until = {"t": 0.0}


# ======================================================
# MAIN
# ======================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="questions.pdf")
    ap.add_argument("--index", default="ancestor-life-story")
    ap.add_argument("--namespace", default="person-001")
    ap.add_argument("--model", default="gpt-4.1-mini")
    ap.add_argument("--embedding", default="text-embedding-3-small")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--tts-src", default=os.environ.get("TTS_SRC", "Text_to_speech/src"))
    ap.add_argument("--tts-mode", choices=["auto", "elevenlabs", "offline"], default=None)
    ap.add_argument("--no-voice", action="store_true", help="answer in text only (STT still on)")
    ap.add_argument("--barge-in", action="store_true", help="force interruption on (use headphones)")
    ap.add_argument("--no-barge-in", action="store_true", help="mute the mic while it talks (use with speakers)")
    ap.add_argument("--language", default="en", help="Deepgram language code, e.g. en, es, multi")
    ap.add_argument("--endpoint-ms", type=int, default=400, help="silence that ends your turn")
    ap.add_argument("--input-device", default=None, help="microphone number or name (see --list-devices)")
    ap.add_argument("--list-devices", action="store_true")
    args = ap.parse_args()

    if args.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        return

    load_dotenv(find_dotenv(), override=True)
    key = os.environ.get("DEEPGRAM_API_KEY")
    if not key:
        sys.exit("DEEPGRAM_API_KEY is missing. Add it to your .env file.")

    # --- RAG setup (same as rag_optimized.py) ---
    docs = rag.parse_pdf(args.path) or rag.fallback_chunks(args.path)
    print(f"Parsed {len(docs)} records from {os.path.basename(args.path)}")
    embeddings = rag.OpenAIEmbeddings(model=args.embedding, dimensions=rag.EMBED_DIM)
    index = rag.get_index(args.index)
    rag.sync_index(index, docs, embeddings, args.namespace, args.path, args.embedding, args.rebuild)
    retriever = rag.Retriever(docs, index, embeddings, args.namespace)

    # --- voice output ---
    speaker = None
    if not args.no_voice:
        try:
            speaker = rag.Speaker(args.tts_src, mode=args.tts_mode)
            print("Voice output: ON")
        except Exception as e:
            print(f"Voice output unavailable ({e}). Answers will be text only.")
    companion = rag.Companion(retriever, args.model, debug=args.debug, speaker=speaker)

    # --- microphone + STT ---
    device = args.input_device
    if device is not None and device.isdigit():
        device = int(device)
    stt = DeepgramSTT(key, language=args.language, endpoint_ms=args.endpoint_ms, device=device)
    try:
        stt.start()
    except Exception as e:
        sys.exit(f"Speech recognition could not start: {e}")
    print("Microphone: ON (Deepgram connected)")
    if args.no_barge_in:
        barge_in = False
    elif args.barge_in:
        barge_in = True
    else:
        barge_in = not output_is_speakers()
        if not barge_in:
            print("Laptop speakers detected: interruption is OFF, because the mic would hear the "
                  "assistant and cut it off. Use headphones, or force it with --barge-in.")
    print(f"Interruption (barge-in): {'ON' if barge_in else 'OFF'}")

    try:
        voice_loop(companion, stt, speaker, barge_in=barge_in)
    except KeyboardInterrupt:
        print("\nGoodbye!")
    finally:
        stt.close()
        if speaker:
            speaker.stop()


if __name__ == "__main__":
    main()
