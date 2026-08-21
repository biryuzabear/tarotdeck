"""The eleven names epd3in7.py needs, plus a model of the controller behind them.

This is not a stub that swallows bytes. It keeps the two RAM planes the way the
SSD1677 keeps them, remembers which mode `init` put the panel in, and rebuilds
the visible image from the stream. That is what makes the emulator able to catch
the mistake the panel would punish: a mono partial issued while four-grey data is
still in the old-image plane, which on glass drives an arbitrary set of pixels in
arbitrary directions rather than drawing text.

`display_1Gray` writes only plane 0x24. Whether the controller then copies it into
0x26 is undocumented, so `mirror_old_plane` does it explicitly and the emulator
assumes nothing.
"""

import time

import waveform
from pins import EPD_BUSY, EPD_CS, EPD_DC, EPD_RST

RST_PIN = EPD_RST
DC_PIN = EPD_DC
CS_PIN = EPD_CS
BUSY_PIN = EPD_BUSY

WIDTH = 280
HEIGHT = 480
LINE = WIDTH // 8
PLANE = LINE * HEIGHT

CMD_SLEEP = 0x10
CMD_UPDATE = 0x20
CMD_LATCH = 0x22
CMD_PLANE_A = 0x24
CMD_PLANE_B = 0x26
CMD_LUT = 0x32
CMD_OPTION = 0x37

FOUR_GREY = "4gray"
MONO = "mono"

on_frame = None
mirror_old_plane = True

_dc = 1
_command = None
_pending = {}
_ram_a = bytes([0xFF]) * PLANE
_ram_b = bytes([0xFF]) * PLANE
_lut = None
_latch = None
_mode = None
_glass = None
_busy_until = 0.0
_asleep = False

warnings = []


def reset_warnings():
    warnings.clear()


def state():
    return {
        "mode": _mode,
        "glass": _glass,
        "asleep": _asleep,
        "warnings": len(warnings),
    }


def _lut_name():
    from waveshare_epd.epd3in7 import EPD

    if _lut is None:
        return "unknown"
    for name in ("lut_4Gray_GC", "lut_1Gray_GC", "lut_1Gray_DU", "lut_1Gray_A2"):
        if list(_lut) == list(getattr(EPD, name)):
            return name
    return "unknown"


_PAIRS = {}


def _pair(byte_a, byte_b):
    key = (byte_a << 8) | byte_b
    out = _PAIRS.get(key)
    if out is None:
        buf = bytearray(8)
        for bit in range(8):
            mask = 0x80 >> bit
            hi = 1 if byte_a & mask else 0
            lo = 1 if byte_b & mask else 0
            if hi and lo:
                buf[bit] = 0xFF
            elif not hi and not lo:
                buf[bit] = 0x00
            elif lo:
                buf[bit] = 0xC0
            else:
                buf[bit] = 0x80
        out = bytes(buf)
        _PAIRS[key] = out
    return out


def _decode(mono):
    if mono:
        return b"".join(_pair(_ram_a[i], _ram_a[i]) for i in range(PLANE))
    return b"".join(_pair(_ram_a[i], _ram_b[i]) for i in range(PLANE))


def _finish_update():
    global _ram_a, _ram_b, _glass
    name = _lut_name()
    mono = name in ("lut_1Gray_A2", "lut_1Gray_DU", "lut_1Gray_GC")
    partial = name == "lut_1Gray_A2"

    if partial and _glass == FOUR_GREY:
        warnings.append(
            "mono partial issued while four-grey data is still in the old-image "
            "plane — on glass this drives arbitrary pixels, not text"
        )
    if mono and _mode == FOUR_GREY:
        warnings.append(f"{name} sent while init(0) mode is latched")

    wrote_b = CMD_PLANE_B in _pending
    if CMD_PLANE_A in _pending:
        _ram_a = bytes(_pending[CMD_PLANE_A][:PLANE].ljust(PLANE, b"\xff"))
    if wrote_b:
        _ram_b = bytes(_pending[CMD_PLANE_B][:PLANE].ljust(PLANE, b"\xff"))
    elif mono and mirror_old_plane:
        _ram_b = _ram_a

    _pending.clear()

    seconds, steps = waveform.parse(_lut)
    flash = waveform.flash(_lut)
    _glass = MONO if mono else FOUR_GREY
    _busy(seconds or 0.05)
    if on_frame:
        on_frame(_decode(mono), name, flash, seconds)


def _busy(seconds):
    global _busy_until
    _busy_until = time.monotonic() + seconds


def module_init():
    global _asleep
    _asleep = False
    return 0


def module_exit(cleanup=False):
    global _asleep, _ram_a, _ram_b, _glass
    _asleep = True
    _ram_a = bytes([0xFF]) * PLANE
    _ram_b = bytes([0xFF]) * PLANE
    _glass = None


def digital_write(pin, value):
    global _dc
    if pin == DC_PIN:
        _dc = value


def digital_read(pin):
    if pin == BUSY_PIN:
        return 1 if time.monotonic() < _busy_until else 0
    return 0


def delay_ms(ms):
    time.sleep(ms / 1000.0)


def spi_writebyte(data):
    _feed(data)


def spi_writebyte2(data):
    _feed(data)


def _feed(data):
    global _command, _lut, _latch, _mode
    if _dc == 0:
        for byte in data:
            _command = byte
            if _command == CMD_UPDATE:
                _finish_update()
        return
    if _command in (CMD_PLANE_A, CMD_PLANE_B):
        _pending[_command] = _pending.get(_command, bytearray()) + bytes(data)
    elif _command == CMD_LUT:
        _lut = bytes(data)
    elif _command == CMD_LATCH:
        _latch = data[0] if data else None
    elif _command == CMD_OPTION:
        _pending.setdefault("option", bytearray()).extend(data)
        option = _pending["option"]
        if len(option) >= 2:
            _mode = FOUR_GREY if option[1] == 0x00 else MONO
            _pending.pop("option", None)


def asleep():
    return _asleep
