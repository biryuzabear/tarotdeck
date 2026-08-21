# The Session

This is the buildable version of [UI.md](UI.md): every screen, every control, every
refresh, the prompt, the reader, and the order to build it in. Where it contradicts
UI.md, it is because a number was measured since. Where a number is unmeasured, it
says so.

Numbers marked *measured* were taken from the files in this repo — the driver's own
LUT tables, the IBM Plex Mono files in `emulator/fonts/`, and all 2000 rows of
`tarot_model/dataset/en/dataset_en.jsonl`. Numbers about the Pi are still research.

---

## 1. The two panel modes, and the rule that governs everything

The SSD1677 has two display modes and the driver's `init(mode)` chooses between
them. `init(0)` is four-grey, `init(1)` is mono. They differ only in the ten bytes
sent on command `0x37`.

`display_4Gray` writes both RAM planes — `0x24` (new image) and `0x26` (old image)
— and latches `0x22 = 0xC7` before the update. `display_1Gray` writes **only**
`0x24`, loads the A2 waveform, and sends no `0x22` at all: it inherits whatever was
latched last. The A2 waveform holds every pixel it does not change, and which
pixels it changes is decided by comparing new RAM against old RAM. So a mono
partial issued while `0x26` still holds the low bit-plane of a four-grey picture
does not draw a line of text on top of a card — it drives an arbitrary set of
pixels in arbitrary directions.

That gives the one rule the whole design obeys:

> **The panel is in exactly one mode at a time. A partial refresh only ever happens
> in mono mode, and mono mode is only ever entered by `init(1)` followed by one full
> mono refresh, which establishes a known old image. No screen ever puts a partial
> on top of a four-grey picture.**

Two consequences worth stating, because they cost real seconds. Every mode switch
costs an `init`, which is at minimum 0.705 s of documented delays (200 + 5 + 200 ms
of reset, plus 300 ms after the `0x12` soft reset) and in truth more, because
`init` also issues `0x46` and `0x47` with `0xF7` — two hardware RAM fills, each
followed by `ReadBusy`, of unmeasured duration. **Treat 0.71 s as a floor, not a
duration.** And every screen that carries greys — the ornamented menu, the card
plates, the standing plate — is a four-grey screen that can never be partially
updated, so anything that needs to change under it needs a mode switch first.

### `lut_1Gray_GC`, the third waveform

Waveshare's driver defines four LUTs and calls three. `lut_1Gray_GC` is dead code.
Parsed through `emulator/waveform.py` it is 38 frames at 25 Hz — **1.52 s with one
visible inversion** — against `lut_4Gray_GC`'s 76 frames, 3.04 s and seven
inversions (both *measured* off the driver's own tables). All four of its
transition planes are driven, so it rebalances every pixel rather than only the
ones that changed. It runs in mono mode.

That makes it the right full refresh for every mono screen: half the time, one
flash instead of seven, and no mode switch on either side of it. It is exposed
through a small `EPD` subclass in the emulator rather than by editing `vendor/`,
which the README says stays unmodified.

### The old-image plane, written by us

`display_1Gray` never writes `0x26`. Whether the controller copies `0x24` into
`0x26` after an update is **not known** — the driver documents nothing and nobody
here has a panel. Rather than depend on it, the mono display path writes the frame
it just showed into `0x26` explicitly after the update completes. It costs another
16 800 bytes over SPI, 33.6 ms at the driver's 4 MHz, and if the controller does
auto-copy the write is identical content and harmless.

This is what makes the append-only argument in §5 true rather than hoped for.

---

## 2. The states

Ten states. Each says what is on the glass, what the four controls do, what it
costs the panel, and what the six lenses and the buzzer are doing.

The LED vocabulary is deliberately small, because six lenses behind a printed
chamfer cannot carry ten meanings. **Colour is the deck's condition, motion means
it is working, and the count of lit rows is where you are in a list.**

| | Means |
|---|---|
| one row amber, steady | your position in a list — a menu row, a card, a page |
| other rows amber, dim | items in that list that exist but are not current |
| rows filling red, bottom up | recording, and how much of the cap is spent |
| one row white, travelling | working — transcribing, or generating |
| all six red, dim, steady | trouble |
| all dark | asleep, or off |

Nothing else. The dim/lit distinction is the only place brightness is load-bearing,
and the page number is on the glass as well, so if the chamfer cannot hold that
distinction nothing is lost but redundancy.

The buzzer clicks on every selection move, rises two notes on confirm, falls two on
back, plays `REVEAL` once per card pitched a step higher each time, and sounds one
low tone at the seal. Nothing per line — twenty-five tones inside a reading is a
metronome, and the buzzer has one voice.

---

### WAKE — power on until the deck can answer

The panel does `init(0)`, then `Clear(0xFF, 0)`, which pulses black-white-black-white
for 3.04 s, then one four-grey splash: the hero sigil from `gravure.py`, the word
TAROT, and nothing else. The splash is not held for a timer. It is held until
`llama-server`'s `/health` returns 200 and one throwaway single-token warm-up comes
back — `--no-warmup` is in RUNTIME.md's flag set, so the genuinely first request
otherwise pays extra. In online mode it is held for `nmcli radio wifi on` plus
association, capped at 8 s rather than waiting on NetworkManager's DHCP timeout.

All four controls are inert and silent. The touch pad is inert too: the pad means
the microphone, and the microphone is not live.

**Refresh:** `init(0)` + 4-grey + 4-grey = 6.79 s, two fulls, fourteen inversions.
That is only affordable because RUNTIME.md's ~10 s cold load of 835 MB is happening
underneath it.

**LEDs:** rows fill amber once for two seconds to show the PiSugar's charge, read
over I²C at 0x57 — the only place battery is ever shown, and it costs no glass.
Then one row travels white until `/health` is green.

**The gap before any of that is a known hole.** WS2812s on GPIO 21 need the kernel
and userspace; nothing in software can acknowledge the power switch in the 20–40 s
before Linux is up, and e-paper holds the previous image with no power, so a
booting deck and an off deck look identical. A oneshot systemd unit early in boot
that writes four bytes to `/dev/leds0` and beeps shortens the gap but does not close
it. The only real fix is a power LED wired to the 5 V rail, which is an enclosure
decision. On the Open list.

---

### SPREAD — the top menu

Top half informs: the gravure ornament at seed 4242, the title, and the current
mode word — `offline` or `online` — small beneath it, so mode is legible without
entering Settings. Bottom half chooses: three rows at the `layout.py` pitch, level
with the three lens pairs.

```
One card      the day, or a plain answer
Two cards     two forces pulling
Three cards   how it moves
```

Each row carries a small ring-via glyph at its left edge, from the gravure
vocabulary, so the rows read as selectable. The **selection itself is not drawn** —
it is the lit lens. That is UI.md's core trick and it survives intact.

- **Right gear** — moves the lit row, wrapping. Zero refreshes. The buzzer clicks
  in step with the light.
- **Left tick right** — takes the lit count into ASK.
- **Left tick left** — into SETTINGS. There is no fourth row, which is why back
  from the top menu is where Settings lives. A small `‹` is drawn at the left edge
  of the divider, because nobody ticks back from the first screen unprompted.
- **Touch pad** — inert. In toggle mode a brush against the bottom edge starts a
  recording rather than being a 200 ms non-event, so the pad is live on exactly one
  screen.

**Refresh:** one four-grey, 3.04 s, on entry. None at all while scrolling.

**LEDs:** one row amber.

> If the chamfer turns out to be illegible in daylight — item 5 on PROGRESS.md's
> unproven list — this menu has no selection indicator at all. The contingency,
> gated on that test print, is to drop the ornament, make the menu a mono screen
> entered with `init(1)` + `1Gray_GC`, and move a drawn caret with one A2 partial
> per step: three partials for a full lap of a three-row menu, inside any reading
> of the five-partial rule. It costs 0.32 s a click and the ornament.

---

### SETTINGS

Mono, no ornament — deliberately not a ritual screen, which is what lets it repaint
cheaply. Three rows, and the current value is the hint text so state is readable
without entering anything:

```
Sound      on
Mode       offline
Power off
```

- **Right gear** — moves the lit row. No repaint.
- **Left tick right** — flips the value on rows 1 and 2 and redraws that row's value
  word alone, one A2 partial. On row 3, powers the deck down: it draws the standing
  plate, sleeps the panel, and calls `systemctl poweroff`.
- **Left tick left** — back to SPREAD. Left is back everywhere, so Settings needs no
  Back row, which is what makes room for Power off.
- **Touch pad** — inert.

**Refresh:** `init(1)` + `1Gray_GC` = 2.23 s on entry; 0.32 s per toggle; `init(0)`
+ four-grey = 3.75 s on the way back to SPREAD. Six seconds to visit Settings and
leave is the price of the mode discipline, and Settings is rare.

The mode toggle is not imperceptible: the ASK screen names the mode, the reading's
footer carries the word, and the thinking light behaves differently (§ TROUBLE and
§7). Flipping it changes something the user can see.

**Power off exists because POWER.md names SD corruption from an unclean cut as the
one real hardware risk, and until now nothing in the flow could halt the machine.**

---

### STANDING — what sits on the glass when the deck is off

The gravure ornament alone, the word TAROT, drawn as the last act of Power off in
four greys, then `epd.sleep()`. E-paper holds it with no power, so this is what
anyone picking the deck up sees, and WAKE replaces it — which makes power-on read
as a change rather than as a start from nothing.

**Refresh:** one four-grey, 3.04 s, then sleep.

The vendor's rule is that the screen must not be left powered and idle, and that it
should be cleared before the deck is put away for a long time. A dark ornament held
for weeks is the image-retention case, so Power off draws the ornament at the two
lightest levels only — paper and faint — never at 0x00. Whether that is enough is
unmeasured.

---

### ASK — speak the question

Mono from here until the reading is sealed. Top line, small: the spread in words
and the mode. The informing half carries one word at 24 px: `speak`. Below the
divider, empty card slots at the row pitch — one, two or three of them, visibly
waiting.

- **Right gear** — inert and silent. There is no list. The missing click is the
  feedback, and no arrow anywhere points at an inert control.
- **Left tick right** — inert. There is nothing to commit until a question exists.
- **Left tick left** — back to SPREAD, `init(0)` + four-grey, 3.75 s.
- **Touch pad** — **tap to start.** The TTP223 is jumpered to toggle mode (B closed,
  A open — one solder blob, no new part) because the chip auto-recalibrates and a
  held touch is reported dropped after 7–15 s, which is inside a normal question,
  and the recalibration control is not brought out on the six-pin package. Both
  edges are treated as one "the pad was touched" event so the chip's latched output
  can never desync from the app's idea of the state. In online mode this tap also
  starts Wi-Fi association, so it hides inside the speaking.

**Refresh:** `init(1)` + `1Gray_GC` = 2.23 s on entry. The deck blinks once and
turns its ear.

**LEDs:** bottom row breathing dim amber — the pad is live. The only invitation on
the device.

---

### LISTEN — the take

One A2 partial replaces `speak` with `listening`, and the line under the divider
reads `tap to stop`. Then nothing on the glass moves for the length of the take.

- **Right gear, left tick right, left tick left** — inert and silent. A tick during
  speech is far more likely to be an accident than an intention, and there is
  nothing on this screen that a tick could mean.
- **Touch pad** — tap to end the take.

The take also ends on 2.0 s of silence (Silero VAD, which whisper.cpp already
ships) or at a 20 s hard cap. Both are mandatory backstops, because toggle mode
gives up the physical guarantee that letting go stops the recording. A take shorter
than 1.5 s, or one with no speech energy in it, is discarded silently and the deck
returns to ASK — that is the brush-against-the-pad case. The 2.0 s silence figure
is a guess to be lived with on the desk; people compose questions out loud with
long pauses, and 1.2 s cuts them off mid-thought.

The microphone has been open since WAKE with a rolling 500 ms pre-roll, prepended
to the take, so the first syllable of "Should I…" survives the device-open latency.

**Refresh:** one A2 partial, 0.32 s, on entry. None during the take.

**LEDs:** rows fill red as the take grows — row 1 at 0 s, row 2 at 7 s, row 3 at
14 s, row 3 pulsing from 18 s to the cap. A level meter that costs no glass, and it
teaches the cap without printing a number.

---

### HEARING — transcribing

Nothing changes on the glass. RUNTIME.md puts `base.en` at 2–4 s for a 10 s clip on
four A76 cores, so a 20 s take is 4–8 s; with `-ac 640 --no-fallback -bs 1 -l en -nt
-t 4` it should be less, but that is unmeasured. This is the one wait in the
pipeline with no picture to look at, which is why it has a state and a light rather
than being left implicit.

All controls inert. A second tap on the pad is ignored until the transcript lands,
so a nervous double-tap cannot start a take over the first.

**Refresh:** none.

**LEDs:** one row travelling white, fast — ~150 ms a step.

---

### CONFIRM — the transcript

One A2 partial draws the transcript, wrapped at 31 columns, from y = 20 at 20 px
leading: eleven lines above the divider, which is 341 characters against the ~290 a
20 s take can produce at ordinary speech. A transcript longer than eleven lines is
truncated with an ellipsis, which is a case the cap makes unlikely and the code has
to handle anyway.

Whisper's leading space and any bracketed non-speech tokens (`[BLANK_AUDIO]`,
`(sighs)`) are stripped before display. An **empty or no-speech transcript never
reaches this screen** — it returns to ASK with the top word replaced by
`heard nothing`, because showing an empty box and asking for approval is worse than
saying nothing. A take that hit the 20 s cap gets one extra line above the
transcript, `it may have cut you off`, and row 1 relabels from `Read it` to
`Read it anyway` — a question clipped mid-sentence reads as a plausible short
question and would otherwise be confirmed straight into a confident, wrong reading.

Three rows below the divider, row 1 lit on entry:

```
Read it
Ask again
Change spread
```

- **Right gear** — moves the lit row. No repaint.
- **Left tick right** — acts on the lit row. The common case is one tick with
  nothing moved.
- **Left tick left** — one step back, and one step back from a transcript is the
  question you did not mean to ask. That is row 2, `Ask again`, and the two coincide
  by design rather than by accident; the row is labelled so the equivalence is
  visible.
- **Touch pad** — inert. The microphone is not live here.

**Refresh:** one A2 partial, 0.32 s. Two partials since the last full.

This screen is the whole answer to Whisper mishearing. A mishear costs 0.32 s and a
re-tap instead of the entire generation wait and a wrong reading. It is a gate, not
a three-second veto window: six lines of monospace take four seconds to read, and a
window shorter than the act it asks for is not a confirmation.

---

### DRAW — the cards turn

Four-grey. `init(0)` once, then one `display_4Gray` per card, 3.04 s each, no added
delay — the waveform is the pacing, and it is about the rate a human turns a card.

**The prompt is built and the request fires before the first card refresh begins**,
so generation and ceremony overlap from the first millisecond.

One card at a time, full width: a plate 240 × 411 px at x = 20, y = 12, which at
0.169 mm a pixel is 40.6 × 69.5 mm — 58 % of a real 70 × 120 mm card, aspect 1.712
against the real 1.714. The name below it at SemiBold 20 (the longest of the 78 is
`Knight of Pentacles` at 19 characters, 228 px against 248 of usable width —
*measured*), and beneath that, small, the word `upright` or `reversed`. A reversed
card's plate is drawn rotated 180°, which is how a real deck shows it, and the name
and the word beneath stay the right way up, so a stranger is not left deciding
whether the screen is broken. The model is forbidden from saying those two words;
the screen is not.

Three across is not an option and the arithmetic is why: at 86 px each a card is
14.5 mm, 21 % scale, on which a Rider-Waite scene shows nothing at all.

**There is no card art yet, and it cannot live in this repo** — CLAUDE.md is text
only, and UI.md says real art will be supplied. So the plate renders the gravure
vocabulary inside a card-shaped frame, and pastes `cards/<slug>.png` over it if that
file exists on the device. The state is buildable today and upgrades without a
redesign, but be honest that the emulator cannot test whether art at 58 % reads.

- **Right gear** — inert.
- **Left tick right** — inert. You cannot hurry a card.
- **Left tick left** — inert. This is the most expensive thing on the device to
  destroy — a spoken question and a wait — and it sits under a spring-loaded gear
  beneath a resting index finger. **No state in this design destroys work on a
  single unconfirmed tick.** Abandoning happens from CONFIRM, before anything has
  been spent, and from TROUBLE, which is a menu.
- **Touch pad** — inert.

**Refresh:** `init(0)` + 3 × 3.04 = 9.83 s for three cards, four fulls. Each
four-grey refresh is itself a charge rebalance, so the reading is entered on settled
glass with the partial count at zero.

**LEDs:** card N lights row N amber and stays lit. The lights count the cards, which
is the same grammar as the menu, not a new one.

---

### HOLD — the last card, while it thinks

Nothing new on the glass; the last card stays up. At RUNTIME.md's ~12 tok/s a
~175-token reading takes ~15 s to generate and the reveals have just spent 9.8 s of
it, so a three-card hold is a genuine 5–7 s spent looking at a card. **There is no
thinking screen in this design.** If the model is slower than modelled, the hold
simply gets longer, which is the most graceful failure available on this panel.

A one-card reading is the opposite case: tone.md gives one card the full 200 tokens,
so generation is the same ~17 s while the reveal cost only 3.75 s, and the hold is
~13 s. That is why the "still working" escalation below counts tokens rather than
seconds.

All controls inert.

**Refresh:** none.

**LEDs:** one row travelling white, slow — one step per ~20 tokens actually received
off the stream, so the light is a generation meter and not an animation, and it is
visibly slower than HEARING's travel. In online mode the response has completed in
2–4 s, so all three rows go steady the moment it lands. That difference is the
honest tell between the two programs. If no token arrives for 12 s the travel
becomes a slow double-blink of row 3 — still here, this is slow.

---

### READ — the reading

`init(1)` + one `1Gray_GC`, which clears the four-grey card and establishes the old
image. Then text appends one completed line at a time, each one A2 partial, at fixed
positions. **Nothing already drawn ever moves.**

Layout, all *measured* against the font files: IBM Plex Mono SemiBold 14, advance
exactly 8.000 px, so 280 − 2 × 16 px of margin = 248 px = **31 columns**.
`ImageDraw.fontmode = "1"`, antialiasing off. 20 px leading. Top margin 14 px, then
22 rows to y = 454, then a 26 px footer strip. Ragged right, never justified: a
monospace can only insert whole 8 px spaces and three of them on a 31-column line is
a visible river. No hyphenation — the longest token in all 2000 readings is 21
characters.

The footer carries the mode word at the left and the page at the right —
`1 / 2  ›` — and it is appended, not moved, at the moment a second page is known to
exist. It costs the reading nothing, because it is not one of the 22 rows.

- **Right gear** — moves between pages. Pages are a list and lists belong to the
  right gear, so the `›` in the footer points at the control that does the thing.
  Inert while page 1 is still filling. Turns are coalesced to a queue of one, latest
  wins, because a free-turning encoder can outrun a 1.52 s refresh.
- **Left tick right** — next page. On the last page, seals it (see below).
- **Left tick left** — previous page. On page 1, back to the last card of DRAW,
  because going back from a reading is going back through the cards it came from;
  from there a second tick returns to SPREAD. One accidental tick never loses a
  reading.
- **Touch pad** — inert. The pad has exactly one job on this device.

**LEDs:** lit row amber = current page, dim amber = the other page that exists. The
travelling light continues while tokens are still arriving and stops at the last
one, so the reader knows the deck has finished speaking before the page has finished
printing.

**The seal.** Tick right on the last page redraws that page in four greys —
`init(0)` + `display_4Gray`, 3.75 s — with the text at 0x00 and the footer rule at
0xC0. Two real things happen: the A2 ink, which was laid down by the shortest drive
the panel has, darkens to true black, and the accumulated charge is rebalanced. The
page visibly settles and stays on the glass. One low tone marks it, earned because
the closing fateful sentence is a structural requirement of the model contract. A
second tick right returns to SPREAD. That third tick is what makes leaving
deliberate rather than one tick past the end of the text.

Whether the A2-versus-GC ink difference is visible on real glass is unknown; if it
is not, the seal is ceremony, and it is the first thing to cut.

---

### TROUBLE

The principle: failure speaks in the deck's voice, never an HTTP code, never a
traceback, never a partial reading presented as a whole one, and always lands on a
three-row menu with a way out.

The mechanism cannot be "one line appended to whatever is up", which is what it
wants to be, because the screen underneath is usually a four-grey card and a mono
partial over four greys is exactly what §1 forbids. So TROUBLE is a mono screen,
entered with `init(1)` + `1Gray_GC` — the same transition the reading was going to
make anyway. It lists the drawn cards as names, one line each, keeps the question
above them, and adds one line in voice:

```
The thread is cut.
```

or `the far voice does not answer; I will speak myself`, or `the reading broke here`
when a stream died mid-print. Three rows:

```
Try again
Ask something else
Back to the start
```

Row 1 re-sends a **byte-identical** prompt. The cards are already named on the
glass, and card selection happens once, before the first request, so a retry can
never contradict what the user is looking at.

- **Right gear** — moves the lit row.
- **Left tick right** — acts on it.
- **Left tick left** — back to ASK.
- **Touch pad** — inert.

**Refresh:** `init(1)` + `1Gray_GC` = 2.23 s.

**LEDs:** all six dim red, steady — the only steady red on the device.

Timeouts. Local: no first token in 25 s. Cloud: 5 s to connect, 8 s to first delta,
25 s total. On a dead cloud stream, retry once silently — the user sees only that
the light is still travelling — then fall through to the local model without
comment, with the footer's mode word reading `offline` when the reading arrives.
Only when there is no local model to fall back to does TROUBLE appear.

**That fallback depends on a contradiction the repo has not resolved.** RUNTIME.md
budgets both models resident at ~1.63 GB against ~2015 MB; PROGRESS.md quotes
~1.22 GB running one at a time. They describe different configurations rather than
disagreeing, but the networked program's silent fallback only exists if the
both-resident figure holds, and nobody has measured it.

---

## 3. The prompt

The user message is not a design choice. It is the shape the model was trained on,
and `emulator/tarot.py:build_prompt` already reproduces it character for character,
reading names and keywords out of `tarot_model/dataset/en/` at runtime so the device
and the training data cannot drift apart.

```
<question> Cards: 1. <Name> (upright|reversed) [<kw, kw, kw>] 2. ... 3. ...
```

One line. Spaces, not newlines — none of the 2000 rows contains a newline, despite
what the example in `system_prompt.txt` implies. Keywords come from `upright.txt` /
`reversed.txt`, one card per line in `Name=kw, kw, kw` form.

Three things are contract, not preference.

**The keyword block is retrieval, and it never reaches the glass.** A 0.8B model
cannot be trusted to recall what the Five of Wands means, so the meaning is looked
up by card and orientation and handed over. The model was trained with the block
present; omitting it moves the distribution. The querent sees the cards; the bracket
behind them is for the model alone.

**The spread never reaches the prompt.** `spreads.md` names Past / Present / Future
and You / Them / The Bond, but no position name enters the string. The training
answers wove the positions out of the question's own wording — one corpus row asks
"What does today have in store for me?" and the answer opens on Morning, Afternoon,
Evening without ever being told. That is why the menu offers a **card count** with a
hint about the shape of a question, and not a labelled spread.

**The model is told the direction and forbidden from naming it.** The words
`upright` and `reversed` appear in the prompt and never in the answer.

### Worked examples, with real keywords from the two files

One card, 152 characters:

```
What do I need to hear right now? Cards: 1. The Moon (reversed) [repressed fear, confusion lifting, deception revealed, inner clarity, misunderstanding]
```

Two cards, 218 characters:

```
Is there anything real between us? Cards: 1. Two of Cups (upright) [partnership, mutual attraction, connection, union, romance] 2. The Devil (reversed) [release, breaking free, reclaiming power, detachment, liberation]
```

Three cards, 278 characters:

```
Will the move to the coast settle anything? Cards: 1. The Tower (upright) [sudden upheaval, chaos, revelation, breakdown, crisis] 2. Eight of Cups (reversed) [fear of moving on, clinging, stagnation, confusion] 3. The Star (upright) [hope, faith, renewal, inspiration, serenity]
```

Corpus user messages average 234 characters, p95 328. All three sit inside the
distribution, so prefill is one or two ubatches and RUNTIME.md's `-ub 64` costs
nothing real.

### The system prompt, cloud only

The local model gets **no system message**. All 2000 training rows are exactly
`(user, assistant)` — there is no system role anywhere in the fine-tune data, so
prepending one pushes the adapter off-distribution. The cloud model gets the
following, saved as `tarot_model/reading_system_prompt.txt` and loaded by path. It
is `system_prompt.txt`'s assistant rules plus tone.md's Voice, Length and Forbidden
sections, with the JSONL-generation scaffolding removed and the ASCII rule made
explicit because zero of the 2000 corpus answers contain a single non-ASCII
character.

```
You are a tarot reader in the Rider-Waite tradition. You are given a question and
the cards that came up, each with its direction and its keywords. You answer with
the reading itself and nothing else.

Voice: a mystical fair foresighter — poetic, fateful, symbolic, intimate. You speak
as if reading from the threads of fate. Not a chatbot, not an assistant. A seer.

Length: 130 to 150 words, never more. One card: spend it all on that one card,
dense, every word earning its place. Two cards: about 80 to 90 words each, plus the
closing line. Three cards: about 55 to 60 each, plus the closing line, which is
tight and forces precision. Never pad. If the reading is said, it is said.

Form:
- Continuous prose. No lists, no headers, no line breaks.
- Plain ASCII only. Letters, digits and ordinary punctuation. No asterisks, no
  markdown, no em dashes, no curly quotes, no ellipsis character, no symbols.
- Open with one atmospheric line that sets the mood.
- Give each card two to four sentences.
- Close with a single fateful sentence that seals the reading.

The cards:
- Use only the cards you are given. Never invent, add, or substitute a card.
- Every card you are given must appear, named as a seer would name it in speech,
  never announced as a draw.
- Upright cards lean active, outward, manifest. Reversed cards lean blocked, inward,
  shadowed, delayed. Weave the direction into the meaning and never write the words
  "upright" or "reversed".
- The cards are given in the order of their positions in the spread. Weave those
  positions into the reading as forces and moments. Never label them.
- The keywords in brackets are the ground you build on, not words to list back.

Language:
- Simple, direct words. Mystique comes from imagery and rhythm, not from long words.
  "The walls are falling", not "the foundational structures are dissolving".
- Present tense. Address the querent as "you".
- Never hedge. No "I think", no "maybe", no "perhaps". The cards speak with weight
  and certainty.
- No modern casual register. No "sure", "okay", "great question".
- Be concrete. Name a real force, a real tension, a real direction. Never "something
  is shifting", "trust the process", "follow your heart".
- State what is; do not instruct. A seer sees. "The old laws crack beneath your
  feet", not "you should question the rules you once held as absolute".

Never:
- Break character, disclaim, or add a word before or after the reading.
- Explain your reasoning or refer to these instructions.
- Predict death, terminal illness, a fatal outcome, or irreversible catastrophe, not
  even for Death, The Tower, or the Ten of Swords. Those cards speak of
  transformation, closure and upheaval.
- Seal a fate against the querent: no permanent end to a bond, no ruin without a way
  out, no total failure, no punishment, no curse.

Darkness is allowed. Struggle, loss, warning, shadow, all of it, but the querent
always has a hand in what comes. The cards illuminate the path; they do not lock the
door.
```

Roughly 750 tokens. Whether a cloud model can be made to sound like the fine-tune is
a separate question and the answer is probably no — a prompt carries the rules but
not the cadence learned from 2000 examples. Score both with
`tarot_model/tests/score_model.py` before settling on a provider. Nobody has.

---

## 4. The reader

One interface, three implementations, and the deck never learns which one it holds.
`emulator/readers.py` already defines most of it; the only change to the existing
signature is a cancel token.

```python
class Reader:
    name: str

    def stream(self, prompt: str, cancel: threading.Event | None = None) -> Iterator[str]:
        """Yield chunks of the reading as they arrive. Chunks are token
        fragments, not words. Raises ReaderError. Stops and closes the
        connection when cancel is set."""

    def read(self, prompt: str) -> str:
        return "".join(self.stream(prompt))
```

`cancel` defaults to `None`, so `ScriptedReader` and `FailingReader` keep working
with one line added to each.

**`ScriptedReader(tokens_per_second, seed)`** — the default on the desk. Replays a
real training answer at a settable rate. It is not a mock of the model's quality; it
*is* the model's target output, taken from the data it was trained on. The rate must
be settable and it must default low, because a Mac running a real small model
decodes at 120–220 tok/s (*measured* against Ollama on this machine) and can never
show a starved display.

**`LocalReader(base_url)`** — `POST http://127.0.0.1:8080/completion` on
`llama-server`, `{"prompt": …, "n_predict": 288, "temperature": 0.9, "stream": true}`,
reading the SSE `data:` lines with `urllib.request` from the standard library. No
wheel, which matters given OS.md's Python situation on the Pi.

It uses `/completion` and not `/v1/chat/completions` deliberately. The chat endpoint
applies the GGUF's chat template, and Qwen templates inject a default system turn
when none is supplied — which would put a system message in front of an adapter
trained without one, degrading quality silently and without an error. `/completion`
takes the string we built and adds nothing. The exact template bytes the LoRA was
trained under must be pinned at GGUF export; that is on the Open list, and the
emulator cannot check it.

**`CloudReader(base_url, api_key, model, system_prompt)`** —
`POST {base_url}/chat/completions` with `stream: true`,
`max_completion_tokens: 288`, `temperature: 0.9`, and
`messages = [system, user]`. `tarot_model/generate.py` already proves the base_url
swap works for OpenAI and Gemini with no other change, so there is no adapter layer
to write. The key comes from `os.environ["OPENAI_API_KEY"]` on the Mac and from
systemd `LoadCredential=api_key:/etc/tarotdeck/api.key` (root:root, 0600) at
`$CREDENTIALS_DIRECTORY/api_key` on the Pi — never `/boot/firmware`, which is FAT,
world-readable, and travels with the card. Scope the key to one project and set a
hard monthly cap; the deck can be lost.

### Streaming semantics

The reader is pumped by its own thread into a `queue.Queue`, never called from the
draw loop. `display_1Gray` blocks inside the driver's own `ReadBusy` for the whole
0.32 s — the emulator makes it block exactly as glass would — so a generator pulled
from the print loop would serialise generation against refresh and cost
`0.32 + 1/rate` per line instead of `max(0.32, lines/rate)`.

Chunks are token fragments — `"The"`, `" Tow"`, `"er"`. The presenter accumulates
them, holds back the trailing partial word until whitespace arrives, and holds back
the trailing partial line until the next word would overflow 31 columns. Display
therefore lags the stream by up to one line, which is correct.

Cloud text additionally goes through `normalize_text()` per chunk before it reaches
the presenter, and `validate(text, card_names)` runs at end of stream. Both are
**reimplemented in the emulator as pure streaming-safe functions** rather than
imported from `generate.py`: that module imports `openai` at module scope, reads
`tarot_model/.env` at import — which CLAUDE.md forbids outright — takes a
`{"messages": …}` dict rather than a string, and ends with `" ".join(text.split())`,
which strips the trailing space off every chunk and runs the words together. The
substitutions to carry over are curly quotes to straight, em dash to comma, en dash
to hyphen, ellipsis to three dots, and asterisk, hash and underscore deleted.

Validation runs after the fact and never wipes a reading the user has already read;
a missing card is logged, not shown.

Thinking stays off. It is off by default on small Qwen3.5 and must remain so —
`<think>` tokens would have to be buffered to the closing tag, which destroys the
overlap the whole design rests on, on top of RUNTIME.md's estimated twenty extra
seconds.

### Errors

`ReaderError` only. The producer thread catches it, drops it into the queue as a
sentinel, and the state machine goes to TROUBLE. Nothing above the reader ever sees
an HTTP status, a socket exception or a traceback. Cancelling is free on the HTTP
path — closing the response makes `llama-server` abort the slot — and the queued but
unprinted words, typically 40–80 because generation runs ahead of printing, are
discarded explicitly rather than flushed.

---

## 5. Text on glass

All of this is *measured* — the font metrics against the files in `emulator/fonts/`,
the pagination against all 2000 corpus readings wrapped at 31 columns.

**IBM Plex Mono SemiBold 14, antialiasing off.** The advance is exactly 8.000 px at
both size 13 and 14, so 13 is strictly dominated — same 31 columns, cap height 9 px
instead of 10. Size 15 is a hinting trap: the advance jumps to 9.000 px, columns
fall to 27, and the cap height drops back to 9. The usable ladder is 12, 14, 16 and
14 is the answer. SemiBold rather than Text because at Text weight most of a glyph's
ink is antialiased edge, which after a mono threshold is a coin flip on every stem;
`ImageDraw.fontmode = "1"` removes the guess entirely, and it matches the
no-antialiasing rule the gravure ornament already follows.

**Geometry.** 16 px side margins over 248 px of usable width = 31 columns. 14 px top
margin, 22 rows at 20 px leading to y = 454, then a 26 px footer strip. Ascent 15 +
descent 4 = 19 px, so 20 px leading clears descenders.

**Pagination, never scrolling.** Wrapped at 31 columns the corpus runs to a median
of 25 lines, p90 28, max 41. Against 22 rows a page: 414 readings fit one page,
1586 need two, and **zero need three**. Page two carries a median of three lines.

Scrolling is ruled out on physics, not taste. It moves every pixel on every step,
which is precisely the charge pattern A2 cannot survive — and it is what
`emulator/deck.py:reading_frame` does today, re-wrapping with `textwrap` and taking
the last sixteen lines on every word.

**Three pages exist in the code even though two are enough in practice.** `n_predict`
and `max_completion_tokens` are 288, not 200, because a cap set at the target
produces `finish_reason: length` — a reading that stops before its closing sentence,
which the user can see, since that sentence is the contract. 288 tokens is at most
~1 600 characters even on a pessimistic characters-per-token figure, which is ~56
lines against 66 rows of capacity across three pages. So the paginator handles up to
three pages, three pages is what the LED strip can show, and 288 tokens cannot
exceed it. Two pages is the measured expectation, not a runtime invariant.

**Append-only.** Text lands at fixed positions and nothing already drawn ever moves.
Balancing 26 lines into 13 + 13 would need the total, which the local program does
not have until generation ends, so a balanced layout would jump the text at the
moment of completion. Unbalanced — 22 then 4 — means no pixel ever moves. The
networked program could balance, since its text arrives whole; it does not, because
the two programs must lay out identically.

### The refresh budget

A three-card local reading from cold, in panel time:

| | Waveform | Time | Count |
|---|---|---|---|
| WAKE `init(0)` + `Clear(0xFF, 0)` | 4Gray_GC | 3.75 s | 1 full |
| splash | 4Gray_GC | 3.04 s | 1 full |
| SPREAD menu | 4Gray_GC | 3.04 s | 1 full |
| scrolling the menu | — | 0.00 s | — |
| ASK `init(1)` + clean | 1Gray_GC | 2.23 s | 1 full |
| LISTEN entry | A2 | 0.32 s | 1 partial |
| CONFIRM transcript | A2 | 0.32 s | 1 partial |
| DRAW `init(0)` + three cards | 4Gray_GC | 9.83 s | 3 fulls |
| HOLD | — | 0.00 s | — |
| READ `init(1)` + clean | 1Gray_GC | 2.23 s | 1 full |
| page 1, 22 lines + footer | A2 | 7.36 s | 23 partials |
| page turn, page 2 whole | 1Gray_GC | 1.52 s | 1 full |
| SEAL `init(0)` | 4Gray_GC | 3.75 s | 1 full |
| back to SPREAD | 4Gray_GC | 3.04 s | 1 full |

**40.43 s of panel time, 11 fulls, 25 partials, maximum 23 partials between fulls.**
A second reading in the same session skips WAKE: 30.6 s and 8 fulls.

Panel time is not wall-clock time. Each mono partial also runs `getbuffer`'s
134 400-iteration Python loop, pushes 16 800 bytes over SPI at the driver's 4 MHz
(33.6 ms), and pushes the same again to mirror `0x26` — about 85–100 ms on top of
0.32 s if a Pi 5 CPython core is four to six times slower than this Mac, where
`getbuffer` runs in 3.2 ms and `getbuffer_4Gray` in 14.3 ms. Call the session ~44 s
of glass work. The Pi figure is unmeasured.

`epd.sleep()` is not in the budget because it is never called inside a burst. The
policy is: **sleep when the deck has been waiting on a human for 90 s, never between
refreshes.** `sleep()` is `0x10` plus a blocking `delay_ms(2000)` plus `module_exit`,
so it must run off the input thread, and deep sleep loses the controller's RAM —
which means the old-image plane the A2 waveform differentiates against is gone.
**Every wake is `init(mode)` plus one full refresh, never a partial.** Read
PINOUT.md's "sleep after every refresh" as "never leave the panel powered and idle",
which is what the wiki text it quotes actually says; taken literally it would add
2.7 s to every line and make a streamed reading impossible.

### Squaring this with the five-partial rule

Twenty-three partials on one page is 4.6× PINOUT.md's `≤ 5`, and the rule is
recorded there as unrepairable if ignored. Three things are true about it.

The number 5 is this project's own convention, not Waveshare's. The wiki text quoted
verbatim in `hardware/parts/epaper-waveshare-3in7.md` says only "after refreshing
partially several times, you need to fully refresh EPD once". No figure.

The rule is about charge balance, which is a per-pixel property, not a frame count.
Decoding `lut_1Gray_A2` shows only two of its five LUTs do anything: black-going
pixels get a single unipolar 8-frame pulse, white-going pixels get the mirror, and
everything else is held, with VCOM flat. Under append-only layout, and with the
old-image plane written after every update so the controller's idea of "unchanged"
tracks the glass, **each pixel is driven exactly once between fulls.** A clock
redrawing its digits drives the same pixels five times in both directions. Twenty-two
append-only partials deposit less charge than two of those.

And that argument is inference from LUT tables, not a measurement. Nobody here has a
panel. So the contingency ships as a constant rather than as a redesign:
`timings.LINES_PER_PARTIAL`, default 1. Set it to 5 and a 22-row page becomes five
partials, which obeys the literal rule with no other change — the reading arrives in
blocks of five lines instead of line by line, and the page loses the quality of
being read to. That is the whole cost.

Line granularity rather than word granularity is a reversal of what UI.md records
("the reading streams a word at a time"). **The reversal was put to the owner with
the arithmetic and accepted: line by line.** A
median reading is 133 words but only 25 lines: word granularity is 133 partials and
42.6 s of panel time against a model that finished in 17 s, and line granularity is
25 partials and 8 s. At 12 tok/s a 31-column line is about 7.8 tokens, 0.65 s of
generation against a 0.32 s refresh, so the panel runs ahead of the model instead of
half a minute behind it. Below about 24 tok/s the panel idles between lines rather
than starving, which means a slower Pi than modelled degrades this design gracefully
and a faster one changes nothing.

---

## 6. The card draw

`Deck.draw(count)` in `emulator/tarot.py` already does it: `random.sample` over the
78 names in `card_names.txt` — without replacement, so no card can come up twice in
one spread — and each drawn card is reversed with probability 0.5, independently.
Keywords are looked up by name and orientation in `upright.txt` / `reversed.txt`.

The cards are drawn **after** the transcript is confirmed and **before** the request
is sent, once, and never again. That is what makes a retry byte-identical and what
stops a retry from contradicting a card the user is looking at.

The spread's positions do not exist as data anywhere on the device. The menu picks a
count. `spreads.md` lists five two-card and six three-card spreads, and the device
reaches none of them by name — which does throw away most of the spread vocabulary
the model was trained across. It is the right trade because the positions were never
in the prompt in the first place: the training answers inferred them from the
question's wording, so naming one in a menu would put a label on the screen that
never reaches the model.

Where they sit is in DRAW, above: one at a time, full width, 240 × 411 px at
(20, 12), name at SemiBold 20 below, orientation word beneath that, reversed plates
rotated 180°. They are not repeated as a footer on the reading page — a three-line
footer would cost the longest readings a third page for no gain, and the cards come
back with one tick left from page 1.

---

## 7. What the emulator fakes and what it runs for real

Unchanged from README.md and still true: the **real, unmodified** `epd3in7.py` runs
over a fake transport that decodes the SPI stream back into pixels; refresh
durations come from the driver's own busy loop rather than being layered on top;
`gpiozero` `Button`, `RotaryEncoder` and `TonalBuzzer` are the real classes on
`MockFactory` pins; the LED chain is a real file written with the same four-bytes-
per-LED semantics as `/dev/leds0`, including the three traps.

What has to change, because the emulator currently flatters the design at exactly
the points that matter:

**The fake transport must model the registers it drops.** Today `fake_epdconfig`
resets `_plane_b` to `None` after every update and falls back to plane A when
decoding, so a mono partial over a four-grey picture renders as clean text instead
of as the mess it would be on glass; `0x22` and `0x37` go on the floor entirely. It
must keep the old-image plane between updates, record the mode set by `init`, record
the latched `0x22`, and **flag any A2 partial issued while the panel is in four-grey
mode**. That single change makes §1's rule checkable, and it lights up on the
current `deck.py` immediately, which calls `init(0)` once and then drives
`display_1Gray` for every word.

**The ghost model must become a drive ledger.** `panel.py:_accumulate_ghost`
accumulates only where ink was erased, so an append-only page — which never erases —
renders flawlessly no matter whether the physics holds. Replace it with a per-pixel
count of A2 drives and their direction since the last full refresh, computed against
the modelled old-image plane, and render A2-written ink one level paler than
GC-written ink so the seal has something visible to do. The counts are honest; the
paleness constant is a guess and should be labelled one, as
`GHOST_PER_FAST_REFRESH` already is.

**`timings.MAX_PARTIALS_BEFORE_FULL` must acquire teeth.** It is read at exactly one
place today, `panel.py:128`, to colour a label orange, and nothing obeys it. It
moves into the refresh authority and forces a full refresh, and the info pane shows
maximum per-pixel drives beside it.

**Voice.** Typed input is the default path and the one that must exist: no
dependencies, runs anywhere, and the only way to feed CONFIRM adversarial
transcripts on purpose — a 50-word question, an empty one, a plausible mishear. A
real microphone with `sounddevice` and a local whisper.cpp sits behind a flag and
must be **padded up to the Pi's honest 2–4 s**, because a Mac that transcribes
instantly designs the wait away. `timings.TOUCH_DROP = 12.0` forces
`controls.touch_up()` while the key is still held, so the TTP223's reported drop is
reproducible on a desk; both mappings live side by side, space held for
hold-to-talk and two taps for toggle, so the interaction can be lived with for an
afternoon instead of settled by ordering a second chip.

**Generation rate.** `ScriptedReader` is the default and its rate is dialled from
12 tok/s downward, so the page can be watched idling and, below the crossover,
lagging. `HttpReader` talks to Ollama on the Mac or `llama-server` on the Pi with
the identical loop.

**Wi-Fi bring-up and the cloud first-token gap** are fixed fake delays, so the
"instant" program is not accidentally instant on the desk.

What cannot be faked and waits for hardware: contact bounce (`gpiozero`'s mock stubs
`_set_bounce`), real contrast and the true ghost rate, whether `lut_1Gray_GC` drives
this panel at all, whether the controller auto-copies `0x24` into `0x26`, LED
brightness through the chamfer, whether the pad reads through the case wall, battery
draw, and card art at 58 % scale.

---

## 8. Build order

Each step is something that can be seen working in the emulator before the next one
starts.

1. **Fix the fake transport.** Keep the old-image plane between updates, record the
   `init` mode and the latched `0x22`, and flag a mono partial issued in four-grey
   mode. Visible immediately: the current `deck.py` trips the flag on its first
   streamed word.
2. **`glass.py`, the refresh authority.** Nothing owns refreshes today —
   `deck.py` calls `display_4Gray` and `display_1Gray` directly, and `panel.py` is
   the pygame window and does not exist on the Pi. `glass.py` owns the mode, the
   inits, the three waveforms including a `display_1Gray_GC` on an `EPD` subclass,
   the `0x26` mirror, the partial counter, and sleep-on-idle. Visible: the info pane
   grows a mode line and a real partial count.
3. **The drive ledger in `panel.py`,** replacing the erase-only ghost, plus pale A2
   ink. Visible: today's scrolling `reading_frame` smears and reports 26 drives on a
   pixel; nothing else changes yet.
4. **`layout.py` grows the geometry** — the 31 × 22 reading grid, the footer strip,
   the card rect, the confirm block. It is 18 lines today and it is the right home
   for all of it.
5. **`typeset.py`** — greedy wrap at 31 columns, pagination to at most three pages,
   an append-only page image at fixed y, and a streaming line emitter that holds
   back the trailing partial word and the trailing partial line. Visible: replace
   `reading_frame` and watch the drive count fall from 26 per pixel to 1.
6. **Rewrite `deck.py` as a state table and `run.py` as an event loop.**
   `confirm()` and `back()` are `if/elif` chains over five string states today and
   do not extend to ten states by four controls. `run.py`'s `submit()` is a
   single-slot queue that silently drops input while a job runs, and `deck.read()`
   is an uninterruptible loop on the worker thread — so a tick during a 10 s reveal
   is swallowed or lands seconds late. Both need replacing: an event queue, a
   dispatch table, and a cancel token threaded through the long jobs.
7. **`readers.py`** — add `cancel` to `stream`, add streaming-safe `normalize_text`
   and `validate`, add `HttpReader`. Visible: `FailingReader` drives TROUBLE end to
   end with no network.
8. **Voice** — typed transcript with a padded delay as the default, the toggle pad,
   `TOUCH_DROP`, silence auto-stop, the cap, and CONFIRM with its empty and clipped
   cases.
9. **Cards** — the plate renderer, the reveal state, the optional
   `cards/<slug>.png` overlay.
10. **The rest of the states** — SETTINGS with Power off, SEAL, STANDING, WAKE
    gated on `/health`.
11. **`HttpReader` against something real** — Ollama on the Mac first, then
    `llama-server` once Phase 4 of `tarot_model/PROGRESS.md` has produced a GGUF.

---

## Open

Ordered by how much each one could invalidate.

**The five-partial rule.** Twenty-three partials a page rests on a per-pixel charge
argument decoded from LUT tables. If the real limit is per-frame,
`LINES_PER_PARTIAL = 5` is the fix and the reading stops feeling spoken. Cheapest
measurement to make once a panel exists, and it invalidates more than any inference
number here.

**The 180-second rule.** PINOUT.md says "refresh no more often than every 180 s" and
`timings.MIN_REFRESH_INTERVAL = 180.0` records it. This design does 36 refreshes in
about a hundred seconds — roughly five hundred times over. No design that is a
device rather than a picture frame can obey it, and Waveshare's own demos do not.
It is kept in `timings.py` as a recorded vendor figure with nothing enforcing it. If
it turns out to be real rather than boilerplate, this deck cannot exist in this form.

**Whether the controller copies `0x24` into `0x26`.** We write the old-image plane
ourselves so it does not matter, at a cost of 33.6 ms per partial. Worth confirming
so the write can be dropped.

**Whether `lut_1Gray_GC` actually drives this panel.** It is dead code in Waveshare's
own driver and nobody in this project has sent it to glass. Three of the four
mono fulls in a cycle use it. If it does not clean, each becomes a four-grey at
3.04 s plus two mode-switch inits, and the cycle goes from ~40 s to well over 50
with seven flashes at every transition instead of one.

**Decode rate on the Pi.** RUNTIME.md's 12 tok/s is explicitly an upper bound from a
benchmark of a dense model, and Qwen3.5's eighteen linear-attention layers are a less
optimised path on ARM. One `llama-bench` run settles whether line granularity is
right.

**Transcription time.** The 2–4 s figure is research. It is the number the whole
listening interaction is designed around and it should be the first thing benched.

**The TTP223 drop.** Seven to fifteen seconds is user-reported, not a vendor spec,
and one circulating claim says the BA6 variant we specified is exempt. A stopwatch
and a finger settle it in five minutes, and the answer decides whether toggle mode
was necessary at all.

**The chamfer.** Already item 5 on PROGRESS.md. This design makes it load-bearing
for the menu, not only for the level meter, so promote it.

**Acknowledging power.** Nothing in software can answer the switch before Linux is
up, and a booting deck looks exactly like an off one. Measure the delay to a oneshot
early-boot LED write; if it exceeds a few seconds the answer is a power LED on the
5 V rail, which is an enclosure change.

**The chat template.** The adapter was trained under MLX-LM with no system message.
The GGUF conversion must carry the same template, and a drift degrades readings
without producing an error. Using `/completion` with a prompt we build ourselves
avoids the injection, but the template bytes still need pinning at export. The
emulator cannot check this.

**Card art.** None exists, none can be committed, and the reveal is the state the
design leans on hardest. Everything about it is provisional until real plates arrive.

**The memory contradiction.** RUNTIME.md's ~1.63 GB with both models resident and
PROGRESS.md's ~1.22 GB with one at a time describe different configurations, and the
networked program's silent fallback to the local model only exists if the first one
holds. Neither has been measured. Whichever is stale should be corrected before
either figure is quoted again.