# Raspberry Pi 5 — 2 GB

The heart of the device.

| | |
|---|---|
| SKU | `SC1110` — Raspberry Pi 5, 2 GB |
| RAM | 2 GB LPDDR4X-4267 |
| Power | 5 V / 5 A USB-C with PD; official 27 W PSU recommended |
| Analog audio out | none — no 3.5 mm jack. Audio is HDMI, USB, or GPIO (I2S/PWM) |
| Specs | https://www.raspberrypi.com/products/raspberry-pi-5/ |
| Product brief | https://pip-assets.raspberrypi.com/categories/892-raspberry-pi-5/documents/RP-008348-DS-6-raspberry-pi-5-product-brief.pdf |

Family: SC1110 = 2 GB, SC1111 = 4 GB, SC1112 = 8 GB, SC1113 = 16 GB.

## Correction: `SC1148`
The listing's `SC1148` is **not the board** — it's the [Active Cooler](https://www.pishop.us/product/raspberry-pi-active-cooler/)
that came with it. Aluminium heatsink + temperature-controlled blower, push-pin
mount, 63.5 × 42.5 × 13.7 mm. https://www.digikey.com/en/products/detail/raspberry-pi/SC1148/21658255

## GPIO on Pi 5
GPIO now sits behind the **RP1** southbridge. Pre-Pi-5 libraries (`RPi.GPIO`,
`pigpio`, `native`) do not work. Use **`lgpio`** — `gpiozero` picks it
automatically. https://gpiozero.readthedocs.io/en/stable/api_pins.html

Hardware PWM channels: PWM0=GPIO12, PWM1=GPIO13, PWM2=GPIO18, PWM3=GPIO19.
