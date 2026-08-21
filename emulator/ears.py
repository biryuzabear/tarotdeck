"""Where the question comes from. One interface, three sources.

The same shape as `readers.py`, and for the same reason: the device has to work
with a real microphone on a Pi, with a real microphone on a Mac, and with neither
— and nothing above this file should know which it has.

Recording is push-to-start, push-to-stop rather than hold. The TTP223 in its
default mode releases a held touch after ten to fifteen seconds even with a finger
still on it, which would cut a question mid-sentence; toggling sidesteps the chip's
behaviour instead of fighting it. There is still a cap, because a pad that is
holding the microphone open is a pad someone forgot about.

Whisper is English-only here, as docs/RUNTIME.md decided. The Russian program is
online, and what it does about transcription is unsettled — noted in Open.
"""

import queue
import threading
import time

RATE = 16000
CAP = 10.0
SILENCE_LEVEL = 0.012
SILENCE_HOLD = 1.6


class EarsError(RuntimeError):
    """Raised when nothing could be heard. The deck shows this, not a traceback."""


class Ears:
    name = "ears"
    live = False

    def start(self):
        """Open the microphone."""

    def stop(self):
        """Close it and return the take, or None if there was nothing."""
        return None

    def transcribe(self, take):
        raise NotImplementedError

    def level(self):
        """0..1, for the lenses. Zero when there is nothing to show."""
        return 0.0


class TypedEars(Ears):
    """No microphone. A fixed question, after a wait the length of a real one."""

    name = "typed"

    def __init__(self, text="what should i know about the week ahead", delay=0.8):
        self.text = text
        self.delay = delay

    def stop(self):
        return "take"

    def transcribe(self, take):
        time.sleep(self.delay)
        return self.text


class Microphone:
    """Capture only. Kept apart from transcription so either can be swapped."""

    def __init__(self, rate=RATE, cap=CAP):
        self.spoke = False
        self.rate = rate
        self.cap = cap
        self.frames = queue.Queue()
        self.stream = None
        self.started = 0.0
        self.peak = 0.0
        self._quiet_since = None

    def start(self):
        import numpy as np
        import sounddevice as sd

        self.frames = queue.Queue()
        self.peak = 0.0
        self.spoke = False
        self._quiet_since = None
        self.started = time.monotonic()

        def feed(indata, _frames, _time, _status):
            block = indata.copy()
            self.frames.put(block)
            self.peak = float(np.abs(block).max())
            if self.peak > SILENCE_LEVEL:
                self.spoke = True

        self.stream = sd.InputStream(
            samplerate=self.rate, channels=1, dtype="float32", callback=feed, blocksize=1024
        )
        self.stream.start()

    def elapsed(self):
        return time.monotonic() - self.started if self.started else 0.0

    def level(self):
        return min(1.0, self.peak * 8)

    def silent_for(self):
        """Seconds of quiet since someone last spoke, so a take can end itself.

        Zero until something has actually been said — otherwise every take would
        end in the first second, before the speaker had drawn breath.
        """
        if not self.spoke:
            return 0.0
        if self.peak > SILENCE_LEVEL:
            self._quiet_since = None
            return 0.0
        if self._quiet_since is None:
            self._quiet_since = time.monotonic()
        return time.monotonic() - self._quiet_since

    def stop(self):
        import numpy as np

        if self.stream is None:
            return None
        self.stream.stop()
        self.stream.close()
        self.stream = None
        blocks = []
        while True:
            try:
                blocks.append(self.frames.get_nowait())
            except queue.Empty:
                break
        if not blocks:
            return None
        return np.concatenate(blocks).flatten()


class WhisperEars(Ears):
    """A real microphone, and Whisper on this machine.

    `mlx-whisper` on a Mac; `whisper.cpp` is what the Pi will run, and the seam is
    `transcribe`, so swapping it is one class and no change above.
    """

    name = "whisper"
    live = True

    def __init__(self, model="mlx-community/whisper-base.en-mlx", cap=CAP):
        self.model = model
        self.microphone = Microphone(cap=cap)
        self.cap = cap
        self.warm = threading.Thread(target=self._warm_up, daemon=True)
        self.warm.start()

    def _warm_up(self):
        """The first call downloads and loads the weights. Do it while the menu is
        still on screen rather than in the silence after a question."""
        try:
            import numpy as np

            import mlx_whisper

            mlx_whisper.transcribe(
                np.zeros(RATE // 2, dtype="float32"), path_or_hf_repo=self.model, fp16=False
            )
        except Exception:
            pass

    def start(self):
        try:
            self.microphone.start()
        except Exception as exc:
            raise EarsError(f"microphone: {exc}") from exc

    def stop(self):
        return self.microphone.stop()

    def level(self):
        return self.microphone.level()

    def elapsed(self):
        return self.microphone.elapsed()

    def silent_for(self):
        return self.microphone.silent_for()

    def transcribe(self, take):
        """Whisper invents words for silence — a blank take reliably comes back as
        "You" or "Thank you." So the take is judged on its own energy before it is
        offered to the model, and a quiet one is refused here rather than turned
        into a question nobody asked."""
        import numpy as np

        if take is None or len(take) < RATE // 4:
            raise EarsError("nothing was said")
        if float(np.abs(take).max()) < SILENCE_LEVEL:
            raise EarsError("nothing was said")
        import mlx_whisper

        try:
            result = mlx_whisper.transcribe(take, path_or_hf_repo=self.model, fp16=False)
        except Exception as exc:
            raise EarsError(f"whisper: {exc}") from exc
        text = (result.get("text") or "").strip()
        if not text:
            raise EarsError("nothing was said")
        return text
