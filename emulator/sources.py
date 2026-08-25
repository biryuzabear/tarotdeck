"""Which reader the deck holds, decided by the mode and by what is reachable.

The device has two programs and they differ only here. Offline talks to a
`llama-server` on the loopback with Wi-Fi down; online talks to an API. Everything
above this file is identical in both, which is the whole reason the reader is an
interface.

On a desk neither may exist, so this degrades rather than fails: it probes, and
falls back to the scripted reader, which replays real training answers. The
emulator says out loud which one it ended up with — a silent fallback would let a
broken endpoint look like a working one.
"""

import os
import urllib.error
import urllib.request
from pathlib import Path

from board import IS_PI, home
from readers import HttpReader, MeaningsReader, ScriptedReader

SYSTEM_PROMPT = Path(__file__).resolve().parent.parent / "tarot_model" / "reading_system_prompt.txt"

LOCAL_URL = os.environ.get("TAROTDECK_LOCAL_URL", "http://127.0.0.1:8080")
LOCAL_CHAT_URL = os.environ.get("TAROTDECK_LOCAL_CHAT_URL", "")
LOCAL_MODEL = os.environ.get("TAROTDECK_LOCAL_MODEL", "")
LOCAL_NAME = os.environ.get("TAROTDECK_LOCAL_NAME", "")

CLOUD_URL = os.environ.get("TAROTDECK_CLOUD_URL", "https://api.openai.com/v1")
CLOUD_MODEL = os.environ.get("TAROTDECK_CLOUD_MODEL", "gpt-4o-mini")
CLOUD_KEY_ENV = "OPENAI_API_KEY"

SCRIPTED_RATE = float(os.environ.get("TAROTDECK_SCRIPTED_RATE", "12"))
WHISPER_MODEL = os.environ.get("TAROTDECK_WHISPER", "mlx-community/whisper-base.en-mlx")

WHISPER_CPP = os.environ.get(
    "TAROTDECK_WHISPER_BIN", str(home() / "whisper.cpp/build/bin/whisper-cli")
)
WHISPER_CPP_MODEL = os.environ.get(
    "TAROTDECK_WHISPER_MODEL", str(home() / "whisper.cpp/models/ggml-base.en.bin")
)
MIC_DEVICE = os.environ.get("TAROTDECK_MIC", "plughw:0,0")


def system_prompt():
    """The cloud model is told in words what the local one was fine-tuned into.

    The local model gets no system message at all: every one of the 2000 training
    rows is a bare (user, assistant) pair, so prepending one pushes the adapter off
    the distribution it learned.
    """
    try:
        return SYSTEM_PROMPT.read_text(encoding="utf-8")
    except OSError:
        return None


def _reachable(url, timeout=1.0):
    try:
        urllib.request.urlopen(url, timeout=timeout).close()
        return True
    except urllib.error.HTTPError:
        return True
    except OSError:
        return False


def local():
    """Chat endpoint first, and that ordering is a measured decision.

    docs/SESSION.md argued for `llama-server`'s `/completion`, on the grounds that a
    chat endpoint applies the GGUF's template and Qwen templates inject a system
    turn the adapter never saw. Our own export says otherwise: fed the bare training
    string it returns an empty completion, and its template injects no system turn
    at all — the prompt begins straight at `<|im_start|>user`. The scaffolding is
    part of what the adapter learned, so it has to be there.

    No system prompt is sent either way. Every one of the 2000 training rows is a
    bare (user, assistant) pair.
    """
    if LOCAL_CHAT_URL and LOCAL_MODEL and _reachable(LOCAL_CHAT_URL.rstrip("/") + "/models"):
        return HttpReader(
            LOCAL_CHAT_URL,
            flavour=HttpReader.CHAT,
            model=LOCAL_MODEL,
            name=LOCAL_NAME or "local model",
        )
    if _reachable(LOCAL_URL + "/health"):
        return HttpReader(LOCAL_URL, flavour=HttpReader.COMPLETION, name="llama-server")
    return None


def cloud():
    key = os.environ.get(CLOUD_KEY_ENV)
    if not key:
        return None
    return HttpReader(
        CLOUD_URL,
        flavour=HttpReader.CHAT,
        model=CLOUD_MODEL,
        api_key=key,
        system_prompt=system_prompt(),
        name=f"cloud {CLOUD_MODEL}",
    )


def ears():
    """A real microphone if this machine has one and Whisper is installed.

    Falls back to a typed question, and says which it got — a silent fallback
    would let a microphone the OS has muted look like a microphone that works.
    """
    import ears as ears_module

    if os.environ.get("TAROTDECK_TYPED"):
        return ears_module.TypedEars()
    if IS_PI:
        if Path(WHISPER_CPP).exists() and Path(WHISPER_CPP_MODEL).exists():
            return ears_module.WhisperCppEars(
                binary=WHISPER_CPP, model=WHISPER_CPP_MODEL, device=MIC_DEVICE
            )
        return ears_module.TypedEars()
    try:
        import mlx_whisper  # noqa: F401
        import sounddevice  # noqa: F401
    except ImportError:
        return ears_module.TypedEars()
    return ears_module.WhisperEars(model=WHISPER_MODEL)


def for_mode(mode, deck=None, language="en"):
    """Three programs now. The third needs neither weights nor a network."""
    if mode == "cards" and deck is not None:
        return MeaningsReader(deck, language)
    reader = cloud() if mode == "online" else local()
    if reader:
        return reader
    if deck is not None:
        # The scripted reader replays a real training answer, which is right for
        # timing and wrong for everything else: it is about three other cards, so a
        # fallback into it puts an interpretation on screen that does not match the
        # spread. The meanings reader is always about the cards actually drawn.
        return MeaningsReader(deck, language)
    return ScriptedReader(tokens_per_second=SCRIPTED_RATE)
