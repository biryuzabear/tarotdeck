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

import os
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

    def elapsed(self):
        return 0.0

    def silent_for(self):
        """Seconds of quiet. Zero from anything that cannot hear, so the take is
        ended by the pad or the cap rather than by silence that was never measured."""
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


class ArecordMicrophone:
    """Capture through ALSA, the way the deck itself has to.

    `sounddevice` would need PortAudio built on the Pi for no gain: `arecord` is
    already there, already the thing we tested the microphone with, and streaming
    its raw output gives the same live level the lenses need.

    The capture gain matters more than the code. This dongle ships with ALSA's `Mic`
    control at 0 of 16 — recordings come out the right length and digitally silent —
    so it is raised on open rather than left to whatever the card last remembered.
    """

    def __init__(self, rate=RATE, cap=CAP, device="plughw:0,0", gain=16):
        self.rate = rate
        self.cap = cap
        self.device = device
        self.gain = gain
        self.proc = None
        self.chunks = []
        self.reader = None
        self.spoke = False
        self.started = 0.0
        self.peak = 0.0
        self._quiet_since = None

    def _set_gain(self):
        import subprocess

        for control, value in (("Mic", str(self.gain)), ("Auto Gain Control", "off")):
            subprocess.run(
                ["amixer", "-c", "0", "sset", control, value],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            )

    def start(self):
        import subprocess

        self._set_gain()
        self.chunks = []
        self.peak = 0.0
        self.spoke = False
        self._quiet_since = None
        self.started = time.monotonic()
        self.proc = subprocess.Popen(
            ["arecord", "-D", self.device, "-f", "S16_LE", "-r", str(self.rate),
             "-c", "1", "-t", "raw"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        self.reader = threading.Thread(target=self._drain, daemon=True)
        self.reader.start()

    def _drain(self):
        import numpy as np

        proc = self.proc
        block = self.rate // 16 * 2          # about 60 ms of 16-bit mono
        while proc and proc.poll() is None:
            data = proc.stdout.read(block)
            if not data:
                break
            self.chunks.append(data)
            samples = np.frombuffer(data, dtype="<i2")
            if samples.size:
                self.peak = float(np.abs(samples).max()) / 32768.0
                if self.peak > SILENCE_LEVEL:
                    self.spoke = True

    def elapsed(self):
        return time.monotonic() - self.started if self.started else 0.0

    def level(self):
        return min(1.0, self.peak * 8)

    def silent_for(self):
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

        if self.proc is None:
            return None
        self.proc.terminate()
        try:
            self.proc.wait(timeout=2)
        except Exception:
            self.proc.kill()
        self.proc = None
        if self.reader:
            self.reader.join(timeout=1)
            self.reader = None
        raw = b"".join(self.chunks)
        raw = raw[: len(raw) // 2 * 2]
        if not raw:
            return None
        return np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0


class WhisperCppEars(Ears):
    """The Pi's ears: ALSA in, `whisper-cli` out.

    Same seam as `WhisperEars` — capture in one object, transcription in a method —
    so which machine this is changes nothing above `Ears`.
    """

    name = "whisper.cpp"
    live = True

    def __init__(self, binary, model, cap=CAP, device="plughw:0,0"):
        self.binary = binary
        self.model = model
        self.cap = cap
        self.microphone = ArecordMicrophone(cap=cap, device=device)

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
        """A quiet take is refused before Whisper ever sees it.

        Whisper invents words for silence — a blank take reliably comes back as
        "You" or "Thank you." Judging the take on its own energy keeps that out.
        """
        import subprocess
        import tempfile
        import wave as wavefile

        import numpy as np

        if take is None or len(take) < RATE // 4:
            raise EarsError("nothing was said")
        if float(np.abs(take).max()) < SILENCE_LEVEL:
            raise EarsError("nothing was said")

        pcm = (np.clip(take, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
            path = handle.name
        with wavefile.open(path, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(RATE)
            out.writeframes(pcm)

        try:
            result = subprocess.run(
                [self.binary, "-m", self.model, "-f", path, "-t", "4", "-nt"],
                capture_output=True, text=True, timeout=120,
            )
        except Exception as exc:
            raise EarsError(f"whisper: {exc}") from exc
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

        if result.returncode != 0:
            tail = (result.stderr or "").strip().splitlines()
            raise EarsError(f"whisper: {tail[-1] if tail else 'failed'}")
        text = " ".join(result.stdout.split())
        if not text or text.strip("[](). ") in ("BLANK_AUDIO", "SILENCE"):
            raise EarsError("nothing was said")
        return text
