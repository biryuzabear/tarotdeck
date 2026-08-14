# Round RGB LEDs — WS2812B

Addressable, single data line. Several of them, loose/discrete, round form.
(The 12-LED ring is a separate part — [led-ring-hs-f12a.md](led-ring-hs-f12a.md).)

| | |
|---|---|
| Chip | WS2812B |
| Protocol | single-wire, GRB order, 800 kHz |
| Voltage | 5 V |
| Form | round modules on board, **10 × 10 mm each** |
| Quantity | plenty on hand; **6–8** planned |

Driving them from a Pi 5 (RP1 broke the old library) and the level-shifter
question are covered in the ring's file — same protocol, and they can be chained
onto the same data line.
