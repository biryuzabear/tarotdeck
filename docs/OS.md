# Operating system

**Raspberry Pi OS Lite 64-bit, Trixie.** Headless, SSH only.

## Why Lite, and why no graphics at all
The e-paper is not a monitor. The Waveshare driver renders into a Pillow image in
memory and pushes bytes over SPI — the kernel never sees a display. So there is
no X, no Wayland, no framebuffer, and nothing to budget for them. Pillow and a
font file, tens of megabytes.

## Why Trixie
Trixie became the default in October 2025; the last non-legacy Bookworm image was
May 2025. Bookworm is now the Legacy channel — security updates only.

| | Trixie | Bookworm (legacy) |
|---|---|---|
| Kernel | 6.18.x | 6.12.x |
| Python | 3.13 | 3.11 |
| Debian support | to 2028-08 | LTS to 2028-06 |
| Idle RAM, Lite | ~230–280 MB | ~230–280 MB — no difference |

**No in-place upgrade.** Bookworm → Trixie means reflashing. Decide once.

## Why not something smaller
Distro choice moves 50–150 MB. Model quantization moves 500–1500 MB. Optimising
the OS is optimising the wrong number.

- **Ubuntu Server** — ~150 MB *heavier*, incomplete and lagging dtoverlay set,
  and Canonical's own docs say Pi 5 wants ≥4 GB.
- **Alpine** — saves the most of any sane option, ~150–200 MB, and its hardware
  support is better than its reputation: it ships `ws2812-pio.dtbo` and the RP1
  PIO driver. The blocker is `lgpio` — not packaged, and gpiozero's Pi 5 pin
  factory needs it, so the whole e-paper path is hand-built against musl. Plus
  OpenRC, no `raspi-config`, and a kernel config nobody else runs.
- **DietPi** — the only one that breaks nothing: same RPi kernel, same
  `config.txt`. Saves ~50–100 MB, but no published measurement is from a 2 GB
  Pi 5, and it currently has an open bug where enabling SPI through its own
  config tool writes to the wrong file and silently does nothing.
- **Buildroot / Yocto** — the right answer for a product, weeks of work for one
  device.

**Disabling services is mostly folklore.** The one clean measurement — removing
triggerhappy, ModemManager, avahi, bluetooth and the serial port — recovered
**12 MB**. Unlike on Pi 4, dropping `vc4-kms-v3d` doesn't help much either: Pi 5
has an IOMMU, there is no `gpu_mem` split, CMA defaults to 64 MB and the kernel
reclaims it under pressure.

## The memory that is actually there
Only ~130 MB of a Pi 5's nominal RAM goes to firmware and kernel reservations.

| | |
|---|---|
| Reported on a 2 GB board | ~2015 MB |
| Pi OS Lite at idle | ~250 MB |
| **Left for us** | **~1750 MB** |

## Two Trixie-specific traps
**`/tmp` is now tmpfs** — it lives in RAM, sized at half of it. Anything written
there is memory, silently. This already bites people: `pip install pillow numpy`
has failed with "No space left on device" on Trixie, and Raspberry Pi's own
tooling hit it. Fix is one line:

```bash
sudo systemctl mask tmp.mount
```

**zram is on by default** (`rpi-swap`) — compressed swap in RAM, new in Trixie.
Keep it. See below for why swap helps us rather than costs us.

## Keep the swap
"Disable swap to free RAM" is wrong twice over: swap lives on disk, so turning it
off frees nothing, and here it actively works in our favour.

llama.cpp `mmap`s the model, so its pages are **file-backed** — they never go to
swap at all, they're just dropped and re-read from the card. What swap evicts is
cold *anonymous* memory: idle daemons, Python heaps. Every megabyte pushed out
there is a megabyte of page cache left for the model.

Corollary: **don't use `--mlock`** with a model this size on 2 GB. Pinning it
turns a slow page-in into a failed start or an OOM kill.

Only real argument against swap is SD-card wear — answered by zram, which is what
Trixie already does.

**Raise `vm.swappiness` to ~100–133.** Pi OS leaves it at 60. Higher sounds
backwards but is right here: the more eagerly the kernel pushes anonymous pages
into zram, the less it needs to evict the model's file-backed pages, which cost
an SD read to get back. The kernel allows up to 200 specifically for compressed
in-memory swap.

**What Trixie actually ships.** `dphys-swapfile` is gone, replaced by Raspberry
Pi's own `rpi-swap`. On a 2 GB board that means a **2048 MiB zram device** at
priority 100 — and `/var/swap` is *not* a swap device any more, it's writeback
storage for pages zram couldn't compress. It also sets `vm.page-cluster=0`, and
leaves swappiness alone. Config lives in `/etc/rpi/swap.conf.d/`; changes need a
reboot. Compression defaults to zstd on the 6.12+ Pi kernel.

## The real risk: SD read speed
If the model doesn't fit, `mmap` re-reads it from the card, and swap cannot help
because file-backed pages never go there.

Random reads on a good A2 microSD run ~7–8k IOPS. NVMe on a Pi 5 does 100–190k —
**20 to 50 times faster**. So "doesn't quite fit" doesn't degrade gracefully; it
turns into a device that takes a minute to answer.

Worth knowing about `--no-mmap`: it makes llama.cpp `malloc` the weights instead,
which makes them *anonymous*, which means zram can compress them. That trades an
SD-read problem for a CPU-decompression one. On a 2 GB box it's a real experiment
to run, not an obvious win either way.

## Tuning: what's worth doing
Everything here totals **25–35 MB**, about 1.5 %. Do it for boot time and tidiness,
not because it solves anything.

- **`max_framebuffers=0`** — the single biggest item here, ~8 MB. Stock is 2. It's
  the legacy pre-KMS console buffer, which a headless box never uses. The
  remaining 4 MB firmware carveout isn't configurable.
- Drop `dtoverlay=vc4-kms-v3d` — headless, nothing renders. A few MB of kernel
  modules, no more.
- `dtoverlay=disable-bt` — but **not** `disable-wifi`. SSH goes over it during
  bench work, and the planned API-backed reading mode needs it at runtime too.
- Disable `ModemManager`, `avahi-daemon`, `triggerhappy`
- Check `rpi-connect` isn't enabled — it's the one service reported to take a
  noticeable chunk
- Mask `apt-daily.timer` and `apt-daily-upgrade.timer` — zero at idle, but they
  can spike tens of MB at the worst moment
- Cap the journal: `RuntimeMaxUse=16M`. On Pi OS since May 2025 the journal is
  `Storage=volatile`, i.e. **in RAM**, defaulting to 10 % of `/run` ≈ 20 MB here

### What's folklore
- **"Disabling Bluetooth frees 50–100 MB"** — no measurement supports it. Both
  `disable-bt` and `disable-wifi` are sub-MB to ~2 MB on Pi 5; the big numbers
  come from pre-Pi-5 articles when the GPU memory split still existed.
- **`dtparam=audio=off`** — Pi 5 has no PWM audio, so it does nothing. And if it
  lands *after* a `dtoverlay=` line it applies to that overlay instead of the
  base tree, which has silently broken HDMI audio for people.
- **"Removing vc4-kms-v3d shrinks CMA"** — it doesn't. The 64 MB pool is declared
  in `bcm2712.dtsi`, with or without the overlay.
- **Shrinking tmpfs** (`/dev/shm`, `/run`) — those sizes are ceilings, not
  reservations. Frees exactly zero.
- **`gpu_mem`** — does nothing on Pi 4 and 5. Stale Pi 3 advice.
- **Shrinking CMA** — 64 MB, movable, reclaimed under pressure anyway.
- **Removing the initramfs** — freed after unpack; saves nothing, risks no boot.
- **Transparent hugepages** — not compiled into the Pi kernel at all.
- **`vm.overcommit_memory=2`** — would count our `mmap`ed model against the commit
  limit and refuse it. Leave overcommit at 0.
- **Raising `vm.min_free_kbytes`** — reserves memory *away* from us.

## Page size
Pi 5 boots `kernel_2712.img` with **16 KB pages**, not 4 KB — check with
`getconf PAGESIZE`. Keep it: four times fewer page faults and TLB entries on a
large `mmap`ed model, plus an officially claimed ~7 % on random access. The cost
is internal fragmentation, unmeasured but plausibly tens of MB. If memory ever
gets desperate, `kernel=kernel8.img` switches to 4 KB and is worth an A/B.

## Python: apt, not pip
`lgpio` has no wheel for Python 3.13 — its last release predates it. In a clean
venv, `pip install lgpio` tries to build from source and fails. People have hit
this.

The supported pattern avoids it and also sidesteps PEP 668, which forbids pip
installing into the system Python from Bookworm onwards:

```bash
sudo apt install python3-lgpio python3-gpiozero python3-spidev python3-pil python3-numpy
python3 -m venv --system-site-packages ~/.venv
```

`spidev`, `pyaudio` and `RPi.GPIO` have no aarch64 wheels either — on *any* Python
version, so this isn't a Trixie problem. All three come from apt. `numpy`,
`Pillow`, `sounddevice` and `gpiozero` are clean on 3.13.

**PiWheels won't save you.** It supports Trixie and 3.13 now, but it only ever
builds `armv6l`/`armv7l` — there are no aarch64 wheels on it at all. On 64-bit it
contributes nothing.

Going the other way has its own cost: Bookworm is frozen at numpy 2.4.6, since
2.5 needs Python ≥3.12, and its apt Pillow is from 2023.

**Don't `import gpiod` directly.** Trixie moved to libgpiod **v2**, whose API is a
hard break from v1, and v1 is gone. `lgpio` and `gpiozero` don't go through it,
so this only matters if a dependency does.

**`RPi.GPIO` does not work on Pi 5** at all — it writes BCM283x registers, and Pi
5 GPIO is behind RP1. `rpi-lgpio` is the drop-in shim if something needs it.

## Waveshare, specifically
The current driver imports only `spidev` and `gpiozero`; Pi 5 support landed
November 2023. Both are apt-installable and 3.13-clean, so the risk is low —
though nobody has publicly confirmed the library on Trixie either way.

**Their wiki is stale.** It still tells you to `sudo pip3 install spidev`, which
now fails outright, and to install `gpiod`, which silently gives v1 on Bookworm
and v2 on Trixie. Ignore it; use the apt line above.

## First boot
Raspberry Pi Imager writes hostname, user, Wi-Fi and an SSH key into the image
before flashing. Card in, power on, `ssh` — no monitor or keyboard at any point.

Then, in `/boot/firmware/config.txt`:
```
dtparam=spi=on
dtoverlay=ws2812-pio,gpio=21,num_leds=8
max_framebuffers=0
```
Keep `max_framebuffers` and any other bootloader-handled option in `config.txt`
itself — they are not read from an `include`d file.
