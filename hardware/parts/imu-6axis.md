# GY-521 / MPU-6050

3-axis gyroscope + 3-axis accelerometer, 6DOF, 16-bit ADC, I²C.

| | |
|---|---|
| Module | GY-521 breakout (AYWHP, 3-pack) |
| Chip | InvenSense/TDK **MPU-6050** |
| Interface | I²C — plain `/dev/i2c-1` device, no RP1 issues |
| I²C address | **0x68** default; **0x69** if AD0 is pulled high |
| Voltage | feed VCC 5 V — onboard 3.3 V regulator; I²C pull-ups go to 3.3 V |
| Chip datasheet | https://www.cdiweb.com/datasheets/invensense/mpu-6050_datasheet_v3%204.pdf |
| Module reference | https://protosupplies.com/product/mpu-6050-gy-521-3-axis-accel-gryo-sensor-module/ |

## Pinout (8-pin header)
| Pin | Function |
|---|---|
| VCC | 5 V in |
| GND | ground |
| SCL | I²C clock |
| SDA | I²C data |
| XDA / XCL | auxiliary I²C, for a slave sensor |
| AD0 | address select — pulled low on-board → 0x68 |
| INT | interrupt output |

## Python
Two working paths, no authoritative recommendation:
- `smbus2` — raw registers; what [SunFounder's Pi 5 guide](https://docs.sunfounder.com/projects/davinci-kit/en/latest/python_pi5/pi5_2.2.6_mpu6050_module_python.html) uses
- [`adafruit-circuitpython-mpu6050`](https://pypi.org/project/adafruit-circuitpython-mpu6050) on Blinka — higher level, maintained

## Caveats
- **The MPU-6050 is end-of-life.** TDK names ICM-42670-P as the replacement.
  Fine for a one-off build, not for a product.
- Clones and remarked parts are widespread; some fail to initialize.
- The on-chip DMP (sensor fusion) depends on an undocumented firmware blob —
  all open support is reverse-engineered and clones may not run it.
