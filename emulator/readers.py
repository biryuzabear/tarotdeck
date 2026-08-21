"""Where a reading comes from. One interface, several sources.

A reader is anything that turns a prompt into a stream of text chunks. The deck
never learns which one it is holding — that is the whole point, because the
device has two programs, local and networked, and they differ only here.

Streaming is not decoration. The panel prints a word per fast refresh, so the
reading appears while it is still being generated rather than after.
"""

import json
import random
import time
from pathlib import Path

DATASET = Path(__file__).resolve().parent.parent / "tarot_model" / "dataset" / "en" / "dataset_en.jsonl"


class ReaderError(RuntimeError):
    """Raised when a reading cannot be produced. The deck shows this, not a traceback."""


class Reader:
    name = "reader"

    def stream(self, prompt, cancel=None):
        """Yield chunks of the reading as they arrive. Chunks are token fragments,
        not words. Raises ReaderError. Stops when `cancel` is set."""
        raise NotImplementedError

    def read(self, prompt, cancel=None):
        return "".join(self.stream(prompt, cancel))


class ScriptedReader(Reader):
    """Replays a real training answer at a chosen rate.

    Not a mock of the model's quality — it *is* the model's target output, taken
    from the data it was trained on, so the emulator shows real prose of the real
    length. Only the choosing is fake.
    """

    name = "scripted"

    def __init__(self, tokens_per_second=6.0, seed=None):
        self.rate = tokens_per_second
        self.random = random.Random(seed)
        self.examples = self._load()

    @staticmethod
    def _load():
        by_count = {1: [], 2: [], 3: []}
        for line in DATASET.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            user = record["messages"][0]["content"]
            count = user.count(") [")
            if count in by_count:
                by_count[count].append(record["messages"][1]["content"])
        return by_count

    def stream(self, prompt, cancel=None):
        count = max(1, min(3, prompt.count(") [")))
        pool = self.examples.get(count) or self.examples[1]
        if not pool:
            raise ReaderError("no scripted readings available")
        text = self.random.choice(pool)
        interval = 1.0 / self.rate if self.rate else 0.0
        for word in text.split(" "):
            if cancel is not None and cancel.is_set():
                return
            if interval:
                time.sleep(interval)
            yield word + " "


class FailingReader(Reader):
    """For exercising the screens nobody designs until they happen."""

    name = "failing"

    def __init__(self, after=8, message="the network is gone"):
        self.after = after
        self.message = message

    def stream(self, prompt, cancel=None):
        for i in range(self.after):
            yield f"word{i} "
        raise ReaderError(self.message)


class HttpReader(Reader):
    """One reader for both programs, because both speak the same wire.

    `llama-server` and every OpenAI-compatible endpoint stream the same way:
    server-sent events, one JSON object per `data:` line, terminated by
    `data: [DONE]`. The only differences are the path, the shape of the request,
    and where the text sits in each event — so those are the only things that vary
    here, and there is no adapter layer.

    **A reasoning model's `<think>` block is dropped, not shown.** Our own export
    opens one and closes it immediately, so its output begins `</think>` before a
    word of the reading; anything reading the stream has to swallow that. Output is
    held back until the closing tag arrives, and released wholesale if it never
    does — at a threshold, and again when the stream ends — so a server that strips
    the block itself is not swallowed whole by a reader waiting for a tag that will
    never come.

    Deliberately `urllib` from the standard library and no SDK. The Pi's Python
    situation is awkward enough without a dependency that has to be built, and the
    whole client is a POST and a loop.

    The local path uses `/completion` rather than `/v1/chat/completions` on purpose.
    The chat endpoint applies the GGUF's own chat template, and Qwen templates
    inject a default system turn when none is given — which would put a system
    message in front of an adapter fine-tuned without one and quietly degrade every
    reading, with no error to notice. `/completion` sends the string we built and
    adds nothing to it.
    """

    COMPLETION = "completion"
    CHAT = "chat"

    THINK_CLOSE = "</think>"
    THINK_GIVE_UP = 400

    def __init__(
        self,
        base_url,
        flavour=COMPLETION,
        model=None,
        api_key=None,
        system_prompt=None,
        max_tokens=288,
        temperature=0.9,
        timeout=120,
        name=None,
        strip_think=True,
    ):
        self.base_url = base_url.rstrip("/")
        self.flavour = flavour
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.name = name or flavour
        self.strip_think = strip_think

    def _request(self, prompt):
        if self.flavour == self.COMPLETION:
            return self.base_url + "/completion", {
                "prompt": prompt,
                "n_predict": self.max_tokens,
                "temperature": self.temperature,
                "stream": True,
            }
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.base_url + "/chat/completions", {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
            "chat_template_kwargs": {"enable_thinking": False},
        }

    @staticmethod
    def _text(event, flavour):
        """Take the reading from wherever the server decided to put it.

        Our own export's chat template opens a `<think>` block, and a server that
        understands reasoning models therefore files the whole answer under
        `reasoning` rather than `content` — measured: two responses in three came
        back with `content` empty and 286 events of `reasoning`, which is what an
        empty reading on the glass actually was. The adapter does not reason; the
        block is scaffolding it was trained through. So whichever field carries
        text, that is the reading.
        """
        if flavour == HttpReader.COMPLETION:
            return event.get("content", "")
        delta = ((event.get("choices") or [{}])[0].get("delta")) or {}
        return delta.get("content") or delta.get("reasoning") or delta.get("reasoning_content") or ""

    def stream(self, prompt, cancel=None):
        import json
        import urllib.error
        import urllib.request

        url, payload = self._request(prompt)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            response = urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            raise ReaderError(f"{self.name}: {exc.code} {exc.reason}") from exc
        except OSError as exc:
            raise ReaderError(f"{self.name}: {exc}") from exc

        thinking = self.strip_think
        held = ""
        try:
            for raw in response:
                if cancel is not None and cancel.is_set():
                    return
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                body = line[5:].strip()
                if body == "[DONE]":
                    break
                try:
                    event = json.loads(body)
                except ValueError:
                    continue
                text = self._text(event, self.flavour)
                if not text:
                    continue
                text = normalize(text)
                if not thinking:
                    yield text
                    continue
                held += text
                cut = held.find(self.THINK_CLOSE)
                if cut >= 0:
                    thinking = False
                    tail = held[cut + len(self.THINK_CLOSE) :].lstrip("\n")
                    held = ""
                    if tail:
                        yield tail
                elif len(held) > self.THINK_GIVE_UP:
                    thinking = False
                    yield held
                    held = ""
            if held:
                yield held
        except OSError as exc:
            raise ReaderError(f"{self.name}: {exc}") from exc
        finally:
            response.close()


_SUBSTITUTIONS = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "—": ",", "–": "-", "…": "...",
    "*": "", "#": "", "_": "",
}


def normalize(chunk):
    """Straighten a chunk without touching its whitespace.

    The training data is plain text — no markdown, no typographic punctuation — but
    a cloud model prompted into the same voice will still reach for em dashes and
    curly quotes. This is reimplemented rather than borrowed from
    `tarot_model/generate.py`, whose version ends with `" ".join(text.split())`:
    correct for a finished string, fatal for a stream, because it strips the
    trailing space off every chunk and runs the words together.
    """
    for bad, good in _SUBSTITUTIONS.items():
        if bad in chunk:
            chunk = chunk.replace(bad, good)
    return chunk


def validate(text, cards):
    """Which drawn cards the reading failed to mention. Logged, never shown — a
    reading the querent has already read is not taken away from them."""
    lowered = text.lower()
    return [name for name, _ in cards if name.lower() not in lowered]


class MeaningsReader(Reader):
    """No model at all. The cards, what they mean, and the rest is yours.

    A third program alongside local and networked, and the only one that needs
    neither a network nor a gigabyte of weights: it reads the same keyword tables
    the prompt is built from and lays them out. Instant, offline, and honest about
    being a lookup rather than a reading — which is why it says so at the end.
    """

    name = "meanings"

    def __init__(self, deck, language="en"):
        self.deck = deck
        self.language = language

    CLOSE = {
        "en": "The cards have said their part. The rest is yours to read.",
        "ru": "Карты сказали своё. Дальше читайте сами.",
    }
    def stream(self, prompt, cancel=None):
        cards = _cards_from_prompt(prompt)
        if not cards:
            raise ReaderError("no cards to describe")
        for name, _turn, keywords in cards:
            if cancel is not None and cancel.is_set():
                return
            yield f"{name}. "
            yield keywords.rstrip(".") + ". "
        yield self.CLOSE.get(self.language, self.CLOSE["en"])


def _cards_from_prompt(prompt):
    """Read back what build_prompt wrote, so this reader needs nothing else."""
    import re

    out = []
    for match in re.finditer(r"\d+\.\s(.+?)\s\((\w+)\)\s\[([^\]]*)\]", prompt):
        out.append((match.group(1), match.group(2), match.group(3)))
    return out
