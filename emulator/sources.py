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

from readers import HttpReader, ScriptedReader

SYSTEM_PROMPT = Path(__file__).resolve().parent.parent / "tarot_model" / "reading_system_prompt.txt"

LOCAL_URL = os.environ.get("TAROTDECK_LOCAL_URL", "http://127.0.0.1:8080")
LOCAL_CHAT_URL = os.environ.get("TAROTDECK_LOCAL_CHAT_URL", "")
LOCAL_MODEL = os.environ.get("TAROTDECK_LOCAL_MODEL", "")

CLOUD_URL = os.environ.get("TAROTDECK_CLOUD_URL", "https://api.openai.com/v1")
CLOUD_MODEL = os.environ.get("TAROTDECK_CLOUD_MODEL", "gpt-4o-mini")
CLOUD_KEY_ENV = "OPENAI_API_KEY"

SCRIPTED_RATE = float(os.environ.get("TAROTDECK_SCRIPTED_RATE", "12"))


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
    if _reachable(LOCAL_URL + "/health"):
        return HttpReader(LOCAL_URL, flavour=HttpReader.COMPLETION, name="llama-server")
    if LOCAL_CHAT_URL and LOCAL_MODEL and _reachable(LOCAL_CHAT_URL.rsplit("/v1", 1)[0] + "/"):
        return HttpReader(
            LOCAL_CHAT_URL,
            flavour=HttpReader.CHAT,
            model=LOCAL_MODEL,
            system_prompt=system_prompt(),
            name=f"local {LOCAL_MODEL}",
        )
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


def for_mode(mode):
    reader = cloud() if mode == "online" else local()
    return reader or ScriptedReader(tokens_per_second=SCRIPTED_RATE)
