"""The eleven names epd3in7.py needs. Decodes the SPI stream back into an image."""

import time

from pins import EPD_BUSY, EPD_CS, EPD_DC, EPD_RST
import waveform

RST_PIN = EPD_RST
DC_PIN = EPD_DC
CS_PIN = EPD_CS
BUSY_PIN = EPD_BUSY

WIDTH = 280
HEIGHT = 480
LINE = WIDTH // 8
PLANE = LINE * HEIGHT

CMD_LUT = 0x32
CMD_PLANE_A = 0x24
CMD_PLANE_B = 0x26
CMD_UPDATE = 0x20
CMD_SLEEP = 0x10

on_frame = None

_dc = 1
_command = None
_plane_a = None
_plane_b = None
_lut = None
_busy_until = 0.0
_asleep = False


def _lut_mode():
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


def _decode():
    if _plane_a is None:
        return None
    a = _plane_a
    b = _plane_b if _plane_b is not None else _plane_a
    n = min(PLANE, len(a), len(b))
    return b"".join(_pair(a[i], b[i]) for i in range(n))


def _finish_update():
    global _plane_a, _plane_b
    duration, _ = waveform.parse(_lut)
    steps = waveform.flash(_lut)
    pixels = _decode()
    _busy(duration)
    if on_frame and pixels is not None:
        on_frame(pixels, _lut_mode(), steps, duration)
    _plane_a = None
    _plane_b = None


def _busy(seconds):
    global _busy_until
    _busy_until = time.monotonic() + seconds


def module_init():
    global _asleep
    _asleep = False
    return 0


def module_exit(cleanup=False):
    global _asleep
    _asleep = True


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
    global _command, _plane_a, _plane_b, _lut
    if _dc == 0:
        for byte in data:
            _command = byte
            if _command == CMD_UPDATE:
                _finish_update()
        return
    if _command == CMD_PLANE_A:
        _plane_a = bytes(data) if _plane_a is None else _plane_a + bytes(data)
    elif _command == CMD_PLANE_B:
        _plane_b = bytes(data) if _plane_b is None else _plane_b + bytes(data)
    elif _command == CMD_LUT:
        _lut = bytes(data)


def asleep():
    return _asleep
