# Power

Battery: [PiSugar 3 Plus](parts/pisugar.md), 5000 mAh single-cell Li-ion at 3.7 V.

## Energy budget
| | |
|---|---|
| Gross | 18.5 Wh (5.0 Ah × 3.7 V) |
| Boost efficiency | **not published by PiSugar** — 87 % assumed |
| Usable at 5 V | **~16 Wh** (calculated) |
| With `bat_protect` on | ~13 Wh — charge caps at ~80 % |

## Pi 5 2 GB draw
Measured at the wall (includes ~10 % PSU loss); the 2 GB board is the frugal one.

| State | Power | Source |
|---|---|---|
| Idle | **2.4 W** | [Geerling](https://www.jeffgeerling.com/blog/2024/new-2gb-pi-5-has-33-smaller-die-30-idle-power-savings/) |
| `stress-ng`, all cores | **8.9 W** | same |

## Runtime — calculated from 16 Wh
The device gets switched off between uses, so runtime is a comfort number, not a
constraint.

| Scenario | Runtime |
|---|---|
| Headless idle, stock | ~7.3 h |
| Headless idle, WiFi and HDMI off | ~8.4 h |
| Light use | ~6–7 h |
| Sustained full load | ~2 h |

No published PiSugar 3 Plus + Pi 5 runtime measurement exists — these are computed.

## The real risk is the 3 A ceiling, not capacity
PiSugar 3 Plus outputs **5 V / 3 A**; the Pi 5 asks for 5 A. Two consequences:

- On a non-5 A supply the firmware **restricts downstream USB to 600 mA** (vs 1.6 A)
  and disables USB boot. Override: `usb_max_current_enable=1` — which lifts the
  limit but does not create current. Not a problem for a microphone: USB audio
  dongles declare 100 mA or less. The limit bites on external SSDs and hubs.
- The Pi's undervoltage trip is 4.63 V, and a boost converter sags as the cell
  drains. Both published failure reports on this combination are this signature —
  random shutdowns and undervoltage warnings **below ~50 % charge**, under load.
  llama.cpp bursts are the hardest current spikes this device will produce.

Nothing here damages hardware. Undervoltage produces a warning; a deeper sag
produces an unclean shutdown. The one thing actually at risk is **SD card
corruption** from being cut off mid-write.

The direct fix is to cap peak draw so the spikes never get there: limit
`arm_freq`, or limit how many threads llama.cpp uses. That trades inference speed
for headroom, and it's a dial we control.

Worth verifying on the actual hardware with an inline USB-C meter.
`vcgencmd pmic_read_adc` cannot see the 5 V rail, so it misses the fan and USB.

## There is a floor
The PMIC sums to **~1.68 W at idle** across its rails, and it can't see the 5 V
rail at all. Against a USB-C meter the real figure is `pmic_W × 1.145 + 0.59`.
So of ~2.7 W headless idle, **~1.8–2.0 W is untouchable** — lowest anyone has
reported is 1.94 W. **Every software tweak combined buys 0.3–0.8 W.**

## Savings, ranked by measured effect
| Technique | Saving |
|---|---|
| `POWER_OFF_ON_HALT=1` + `WAIT_FOR_POWER_BUTTON=1` → PMIC STANDBY | down to **~15 mW** with RTC wake |
| `dtoverlay=disable-wifi` + `disable-bt` | **~0.19 W** — cleanest measurement in the set |
| Undervolt `over_voltage_delta=-89000` | core 0.899 → 0.810 V measured; watts never measured |
| Cap `arm_freq` | ~0.2 W off peak; **no idle effect** — DVFS already scales voltage |

Measured nulls, don't bother: CPU governor choice (ondemand vs schedutil vs
min-clock — all ~2.7 W), disabling HDMI (65 mW of it is EDID EEPROM that can't be
switched off at all; blanking saves 10 mW), turning LEDs off (<10 mW, and that was
measured on a Pi 4).

`arm_freq_min=500` is stale advice — it mattered before Jan 2024 kernels, doesn't
now, and official docs say it isn't supported.

Reject: the widely-copied claim that `power_force_3v3_pwm=1` saves 0.1–0.3 W. It
forces PWM, which is *less* efficient than pulse-skipping at light load, so it
should raise idle draw. No primary measurement either way.

Active Cooler fan draw is published nowhere and sits on the 5 V rail the PMIC
can't read. Raising `fan_temp` thresholds also runs the SoC hotter, which raises
leakage and partly cancels the saving.

## Not applicable: deep sleep
Standby modes get a lot of airtime in power guides, but a sleeping device isn't
doing the thing it exists to do. The deck is switched off between uses and awake
when it's in use. There is no idle to optimize away.

WiFi, Bluetooth, HDMI and anything else unneeded can simply be off — the deck
never needs them.
