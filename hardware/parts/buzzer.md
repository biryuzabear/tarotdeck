# Passive buzzer

Considered instead of a speaker: a speaker doesn't really fit, and a buzzer
suits the retro aesthetic better.

**Passive**, not active. The difference matters:
- **Active** buzzer has an internal oscillator — apply DC, it beeps at one fixed
  factory-set pitch. On/off only.
- **Passive** buzzer is a bare transducer — silent on DC, and sounds at whatever
  frequency you feed it. Drive it with **PWM at 50 % duty**; the frequency is the
  note. So it can play different pitches and simple melodies.

| | |
|---|---|
| Type | passive |
| Drive | PWM, 50 % duty; frequency sets pitch |
| Useful range | piezo elements resonate ~2–4 kHz, usable ~2–6 kHz — loudest at resonance, thin and quiet outside it |
| Model | ? |

## Direct GPIO or transistor?
Depends which kind it is:
- **Piezo** — capacitive, ~1 mA at 3 V. Fine driven straight from a GPIO pin.
- **Magnetic** — a coil, 20–100 mA. Exceeds safe Pi GPIO drive (~16 mA/pin);
  needs an NPN transistor (2N2222/BC547, ~1 kΩ base resistor) and a flyback diode.

If it's on a module board (KY-006/KY-012 style) the driver transistor is already
there. If unlabelled and bare, a ~100 Ω series resistor is a cheap safeguard.

## Python on Pi 5
`gpiozero.TonalBuzzer` — `play()` takes note names, Hz, or MIDI numbers.
`RPi.GPIO` does not work on Pi 5; gpiozero on the lgpio factory does.

```python
from gpiozero import TonalBuzzer
from time import sleep

b = TonalBuzzer(17)
for note in ["C4", "E4", "G4", "C5"]:
    b.play(note); sleep(0.3)
b.stop()
```

This is software PWM and can jitter under load. For clean tones the Pi 5 has 4
hardware PWM channels (GPIO12/13/18/19) via `dtoverlay=pwm`, driven from
[`rpi-hardware-pwm`](https://pypi.org/project/rpi-hardware-pwm).

Docs: https://gpiozero.readthedocs.io/en/stable/api_output.html
