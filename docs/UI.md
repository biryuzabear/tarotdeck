# Interaction

## The session, as described
Screen on top, controls below or on the side.

1. **Switch on.** A physical button or switch, placed where the Pi's own power
   button is.
2. **Pick a program.** At first there may be only one — the tarot reading — but
   the intent is a choice of programs.
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
The **LED strip** carries transient state; the e-paper is too slow for anything
that changes per click and shouldn't be repainted for it.

Scrolling costs no repaint at all: the e-paper draws the menu once and the LEDs
move the selection along it.

**The OLED is dropped** — it fits between the gears, but 27 × 27 mm of module
buys only a running line of text.

Open, as a result: how the transcribed question gets confirmed.
- one extra 3 s repaint showing the question, tick right to accept — catches
  mistakes before the model runs
- or no repaint at all, the question printed above the reading on the same page —
  quieter, but a misheard question costs the whole wait

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

## Open
- What two- and three-card spreads are *for*
- How many controls this actually needs
- How the elements are laid out physically
