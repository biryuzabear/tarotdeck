"""Which machine this is running on.

The one place that asks. Everything else imports `IS_PI` and picks a backend from
it, so there is never a second, differently-worded guess somewhere down the tree.
"""

from pathlib import Path

MODEL = Path("/proc/device-tree/model")


def _is_pi():
    try:
        return "raspberry pi" in MODEL.read_text(errors="ignore").lower()
    except OSError:
        return False


IS_PI = _is_pi()


def home():
    """The person's home, not root's.

    `/dev/leds0` is root-owned, so the deck runs under sudo — and `Path.home()` then
    points at `/root`, where nothing of ours is installed. Whisper and the model both
    live in the user's tree, so that is the one to ask for.
    """
    import os
    import pwd

    who = os.environ.get("SUDO_USER")
    if who:
        try:
            return Path(pwd.getpwnam(who).pw_dir)
        except KeyError:
            pass
    return Path.home()
