# LED ring `HS-F12A`

**Dropped from the build.** The screen is centred across the 76 mm face, leaving
~10.5 mm strips down each side — a 40 mm ring fits nowhere. Kept here because the
WS2812 driving notes below apply to the loose round LEDs too.

Addressable RGB ring from **Hello STEM** ("A series" actuators).

| | |
|---|---|
| LEDs | **12 ×** WS2812 5050, wired in series |
| Protocol | single-wire WS2812, **GRB order, 800 kHz** |
| Voltage | 3.3 V / 5 V |
| Size | ring PCB **40 mm** diameter, 49 mm overall including the header tab, 3.2 mm mounting holes |
| Vendor page | http://www.hellostem.cn/en/zhi-xing-qi/165.html |
| Dimension drawing | http://www.hellostem.cn/uploads/2_chuanganqi/hs-f12a/10-Size.jpg |

## Pinout — 4-pin 2.54 mm header: `G / V / R / D`
- `G` = GND, `V` = V+
- **`R` = data IN** — the odd label, easy to misread
- `D` = data OUT, for chaining

Board also has a power indicator LED and a direction arrow in silkscreen.

Variant `HS-F12PA` is the same ring with a 3-pin PH2.0 connector and a single
`S` signal pin, no DOUT.

**Unconfirmed:** whether the LEDs are specifically WS2812**B** — the vendor says
only "WS2812".

## Driving WS2812 from a Pi 5
The old `rpi_ws281x` DMA/PWM path is broken by RP1. Current options, best first:

1. **`ws2812-pio` device-tree overlay** — official, in Raspberry Pi OS, uses the
   RP1's PIO block so timing is hardware-generated. `dtoverlay=ws2812-pio,gpio=18,num_leds=12`
   creates `/dev/leds0`. Pi 5 only. https://github.com/raspberrypi/firmware/blob/master/boot/overlays/README
2. **[Adafruit Blinka Pi 5 NeoPixel](https://github.com/adafruit/Adafruit_Blinka_Raspberry_Pi5_Neopixel)** — Python, PIO via `/dev/pio0`, familiar NeoPixel API
3. **SPI/MOSI bit-bang** — [`rpi5-ws2812`](https://github.com/niklasr22/rpi5-ws2812); costs the SPI bus, which the e-Paper also wants
4. `rpi_ws281x` Pi 5 support exists but is explicitly experimental

**Level shifter:** Pi GPIO is 3.3 V, WS2812B data-high wants ~0.7 × VDD (3.5 V at
5 V supply) — technically out of spec. Adafruit recommends a **74AHCT125**. At 12
LEDs on a short lead it will likely work directly; use the shifter for reliability.
https://learn.adafruit.com/neopixels-on-raspberry-pi/raspberry-pi-wiring
