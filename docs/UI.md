# Interaction

## The session, as described
Screen on top, controls below or on the side.

1. **Switch on.** A physical button or switch, placed where the Pi's own power
   button is.
2. **Pick a program.** Two of them — see below.
3. **Splash screen** for the chosen program.
4. **Pick a spread:** one, two, or three cards, each with a hint about what it's
   for (one card = card of the day, or a simple question; two and three still to
   be defined). A vertical menu of three, scrolled.
5. **Speak the question.** Press a button to talk, then press again to confirm —
   or to erase and redo.
6. **The model works.** Meanwhile the cards that came up are shown one at a time.
   Not an animation, just sequential reveal. The buzzer plays something.
7. **The reading appears.**
8. Then another spread can be chosen.

## The two programs
The choice at power-on is between a **local** reading and a **networked** one.
This is the point of the device having a menu at all.

|  | Local | Networked |
|---|---|---|
| Wi-Fi | off | on |
| Loads | the tarot model, and Whisper | Whisper only |
| Speed | slow — it thinks | close to instant |

The local one is the device as originally conceived: nothing leaves it. The
networked one hands the reading to an API — Codex, or whatever is cheap — and
answers immediately.

Whisper stays on the device in both, most likely: transcription should be fast
enough locally that sending audio away buys nothing. It could go over the network
too, but there's no reason yet.

Open: how the two feel different beyond the wait. If one is instant and the other
takes half a minute, the slow one had better be the one that feels like the real
thing.

## Controls, as imagined
Selection wants a **wheel on the side** — like a volume knob, but clicking:
turn to move through a list, press it to choose. Or a separate button underneath
for confirming.

Buttons that seem needed: confirm, a big hold-to-talk one, and something for
scrolling.

## Current layout
Held **gripped from both sides with two hands**, index fingers resting on the top
edge and doing the work. Thumbs just steady it. That inverted grip is what makes
it feel unlike a normal device.

**Both top corners are gears.** One under each index finger.

- **Right gear — turns freely.** This is the encoder: scrolling, moving through
  lists.
- **Left gear — spring-centred.** It only ticks a little one way or the other and
  returns to neutral. Tick right = yes / forward. Tick left = no / back.
- **Top edge, between them:** microphone slots
- **Left side:** the LED strip
- **Bottom:** the dictation control — touch pad or physical button, still open

This settles the encoder-press problem: the right gear never needs pressing,
because confirm moved to the left gear.

Right hand moves forward and confirms, left hand goes back. The dictation button
is separate and large because talking is the one deliberate act.

## How it's held — thinking in progress
**Game Boy layout, considered and set aside.** Two buttons at the bottom under
the thumbs, left = back, right = confirm, scroll wheel under the index finger.
Reads as too obvious — it's just a Game Boy — and the bottom grip on this device
is much shorter than a Game Boy's, because the screen takes up most of the face.

The screen is not touch, so covering it with hands is pointless anyway.

**Held like a tarot deck, from the side.** The thumb rests on the long edge, and
scrolling there is the natural gesture. Best guess is the encoder mounted with
its shaft out through the side wall — but how that feels to use, and how it
looks, is unresolved.

**Held upside down** — sounds better. The heavy end goes to the bottom, and the
free space is then at the top: wheel on the right, back button on the left, and
room for a microphone grille at the top, which is where you'd want to speak into
anyway.

## Weight
The top of the device is noticeably heavier than the bottom, which is wrong for
something you hold. The only mass that can move is the **battery** — it's on a
magnet, so it can be shifted down.

## Lit chamfer
The round LEDs come already mounted on board, **10 × 10 mm each**. Six to eight
of them run down the side of the screen, alongside the menu, marking which item
is selected.

Eight at 10 mm is 80 mm, and the screen's active area is 81.12 mm tall. They line
up almost exactly — one LED per menu row.

**Not holes — a chamfer.** The case edge is cut away at 45° along the length of
the screen, and the light comes out through that bevel. Visible head-on and from
the side both. One lit edge rather than a row of dots — a part of the object, not
a perforation.

It also stops reading as asymmetry: a lit bevel is edge treatment, not something
sitting on the face.

**Tilting the board 45° is what makes it fit.** A 10 mm board tilted 45° projects
10 / √2 = **7.07 mm** of width. With 1.5 mm walls the inner width is 73 mm, the
block takes 58, leaving 7.5 mm each side — so the screen can stay **centred**,
and both edges can be lit. Symmetry recovered.

At 2 mm walls each side is exactly 7.0 mm, which misses by 0.07 mm. So this
depends on 1.5 mm walls.

Still to check: the board's real thickness with its connector and wiring soldered
on, which adds to the 7.07.

## Two things to get right
**Diffusion.** A bare WS2812 behind a hole is a harsh point of light. Leave the
chamfer as a thin 0.8–1 mm wall rather than cutting through — printed PLA at that
thickness diffuses well.

**Bleed.** The LEDs sit 10 mm apart with wide beams. Without a solid rib between
each pair, running to the wall, the spots merge into a smear — which destroys the
whole point, since what's wanted is one crisp light against one menu row.

## Indication
The **LED strip** carries transient state. Even at 0.3 s the e-paper is too slow
for something that changes on every click of the encoder.

Scrolling costs no repaint at all: the e-paper draws the menu once and the LEDs
move the selection along it. This also spends no ghosting budget.

**The OLED is dropped** — it fits between the gears, but 27 × 27 mm of module
buys only a running line of text.

**The 3 s figure is only for four-grey refreshes.** Mono refreshes run ~0.3 s, and
`display_1Gray` in the Waveshare driver already does them — nothing to write. Text
is black on white anyway, so mono costs us nothing.

That changes what the screen can do. Within a state it can carry a **live region**
updated at 0.3 s while the rest stays put:

- **The reading can print as it generates, one line per fast refresh** — decided,
  reversing an earlier note that said one word per refresh. A typical reading is
  133 words but only 25 lines: by word it costs 133 partials and 42 s of panel
  time against a model that finished in 17; by line it costs 25 partials and 8 s,
  and a 31-column line takes about 0.65 s to generate against a 0.32 s refresh, so
  the panel waits on the model instead of trailing it by half a minute.
- **The transcribed question gets shown** for confirmation. This used to be a
  dilemma — spend 3 s on it or risk a misheard question costing the whole wait.
  At 0.3 s there's no dilemma.

The state machine still holds: each screen is drawn once on entry. But a state may
own a region that keeps moving.

**The cost is ghosting.** A2 is the most ghost-prone waveform, and the panel is
damaged permanently if it never gets a clean full refresh. So the code carries a
counter: N fast updates, then one full. Vendor guidance says N ≤ 5; whether that's
real or cautious is worth measuring.

## Face geometry
**Width is set by the driver board, not the panel.** The board is 58 mm and sits
right behind the 54.9 mm panel, so the narrower panel buys nothing — 58 mm is the
widest thing in the device, wider even than the Pi at 56 mm.

Against the 76 mm envelope that leaves **18 mm total** across the width, ~9 mm a
side if centred. Along the 126 mm length the driver board is 96.5 mm, leaving
**~29 mm** at one end.

**The screen is centred across the width.** Along the length it can be offset.

Consequences:
- **The LED ring is out.** 40 mm doesn't fit anywhere. Dropped.
- A 5050 LED is 5 × 5 mm, so a strip of them still fits a 9 mm side strip.
- An encoder body is ~12 × 12 mm — it does **not** fit beside the screen. It has
  to live on the edge wall or at the end.

The ~29 mm end is the only real estate for the microphone grille and controls,
and in the upside-down orientation it lands at the top, where you'd speak into it.

## Menus, as settled
No program choice at power-on. The first menu is the spread — one, two or three
cards — plus **Settings**, which holds the sound switch and the offline/online
mode. Choosing a spread goes straight to hold-and-speak.

The device is held **portrait, always** — there is no landscape mode.

**The free strip moves to the bottom.** The driver board is 96.5 mm in a 126 mm
body, and that 29.5 mm of slack now sits under the glass rather than above it,
giving the dictation pad ~21 mm of face. The board cannot go higher than 16 mm
from the top: the encoder body is ~12 mm across, the board is 58 mm wide leaving
only 9 mm of corner outside it, so the gears have to sit *above* the board and
that is what sets the floor.

**Two thirds of each lens is visible.** The chamfer is cut at 45 degrees, so the
outer third of the LED disappears into the bevel and what reads from the front is
a flat-sided crescent, cut on the outside, facing the screen.

The screen splits in two: the **top informs**, the **bottom chooses**. Menu rows
live in the lower ~44 % of the glass, and the LEDs are level with them.

Both chamfers light together: one menu row is two LEDs, mirrored. **Three rows,
six LEDs on the chain** — a menu never needs more than three items, so one lit
row is one menu line, and the rows are big enough to read at arm's length.

Three items also means Settings has no slot in the list. It is reached by ticking
the left gear back from the top menu, where there is otherwise nowhere to go.

The buzzer clicks on every scroll step, in step with the light.

## The gravure ornament
The visual language of biryuzabear.github.io and the bot cards. **Card faces are
not generated** — real art will be supplied. The generator's vocabulary dresses
the informing half of the menu instead.

What the reference actually does, and what the port reproduces:

- **One hero sigil, open rather than woven.** Outer circle, a second circle well
  inside it, an inscribed diamond with its two diagonals, and at the centre a
  star-cog ringed by bolt holes. Few elements, far apart.
- **The cog sits on top and nothing crosses it.** A disc of paper is punched out
  before it is drawn, so the diamond and its diagonals stop at its edge instead
  of running through it. That clearance is most of why the centre reads clean.
- **Circles talk to each other around the hero.** A satellite runs a radial stub
  out to a bus radius, the bus carries it round the hero as an arc, and another
  stub drops into the next satellite, with a via at each end. Because the
  informing half is wide and short, there is no room for an orbit above and below
  the hero: the satellites sit out to the sides and the bus goes over the top or
  under the bottom, chosen by the seed.
- **Traces hug the frame, and stay short.** Orthogonal runs in bundles of two or
  three, cornered at 45 degrees, ending in a small ring via. They travel down the
  margins and across the corners; they never radiate out of the sigil. Kept
  deliberately stubby — the screen is 47 mm wide and a long run just clutters it.
- **Depth by layer.** Background sigils and the long runs sit one grey lighter
  than the hero — which is how the reference uses opacity, and it maps exactly
  onto the panel's four levels: paper, faint, ornament, text.

Two rules keep it legible on glass rather than in a browser:

- **Nothing thinner or closer than the panel can separate.** Every radius is
  checked against the ones already used, a polygon is refused when its edge would
  fall below 12 px, dots have a floor. At 0.169 mm a pixel, strokes closer than
  7 px read as one smudge. Elements are dropped, never squeezed.
- **No antialiasing.** Drawn at final size with one-pixel strokes. A resampled
  line lands as mid-grey on a four-level panel, which was exactly the mush the
  first attempt produced.

## Open
- What two- and three-card spreads are *for*
- Where one, two and three cards sit on a 280 x 480 screen
- Where the reading text goes once the cards are on screen
- How many controls this actually needs
- How the elements are laid out physically
