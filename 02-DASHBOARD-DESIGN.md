# 02 — Dashboard Design

Single file. `dashboard.html`. No build step, no framework, no npm. Vanilla JS and CSS custom
properties, served by `python -m http.server`. If it needs a bundler at 9am tomorrow, it's wrong.

---

## Design direction: the dispatch rack

The reference isn't a SaaS analytics dashboard. It's an **air traffic control flight-progress
board** — the rack of paper strips a controller slides through positions as each flight moves
through its phases. That artifact maps onto this problem almost exactly: one strip per unit of work,
annotated as it progresses, physically moved when it clears.

So: agents are **strips**, not cards. They slide in when spawned, carry live annotation while
working, and clear downward when done. Retries clip beneath their parent like an amended strip.

This buys three things a card grid doesn't:
- **Density without clutter.** 8 strips read at a glance; 8 cards need scrolling on a projector.
- **Legible parallelism.** Horizontal work-traces running side by side make simultaneity obvious in
  a way that spinner icons never do.
- **A real place for the loop.** Nested amendment strips are a genuine ATC convention, so the retry
  visual encodes something true instead of decorating.

Deliberately avoided: near-black + acid-green terminal, glassmorphism, gradient stat tiles. Those
read as "AI made a dashboard." The palette below is CRT-amber ops room on a blue-black hangar
ground — high contrast for a bad projector in a dark room.

### Tokens

```css
:root {
  /* Ground */
  --hangar:   #101A2B;  /* page background — navy-black, not pure black */
  --rack:     #18263D;  /* strip surface */
  --rack-hi:  #1F3050;  /* hovered / active strip */
  --rule:     #2C3E5C;  /* hairlines, 1px */

  /* Ink */
  --chalk:    #E8EDF5;  /* primary text */
  --dim:      #8296B3;  /* labels, metadata */

  /* Signal — used sparingly, this is the accent */
  --signal:   #FFB020;  /* active work, the pulse, the scanline */
  --verified: #4ED2A0;  /* passed */
  --fault:    #FF5C5C;  /* failed */
  --urgent:   #FF8A3D;  /* high-severity finding */
}
```

Rule: **amber is the only accent.** Mint and red are semantic status only, never decoration. If
something isn't actively working, passed, or broken, it's chalk or dim.

### Type

| Role | Face | Use |
|---|---|---|
| Display | **Saira Condensed**, 600/700, tracked +0.04em, uppercase | Board title, section headers, status words. Transit-signage energy, condensed so it stays big without wrapping. |
| Body | **IBM Plex Sans**, 400/500 | Finding summaries, notes |
| Data | **IBM Plex Mono**, 400/600 | Every number, id, timer, counter — *all* of them |

Same superfamily for body and data keeps it cohesive; the condensed display face carries the
personality. One Google Fonts link, and **download the woff2 files locally tonight** — venue wifi is
not your friend, and a font fallback will visibly wreck the layout mid-demo.

Scale: `11px` labels / `13px` data / `15px` body / `22px` strip titles / `40px` board title.
Bump everything 20% if you're on a projector rather than a monitor — put it behind a `?big=1` flag
so you can flip it in the room.

---

## Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ GLASS BOX · <mission>                          00:42 ▐ ● LIVE        │  ← rail, 64px
├──────────────────────────────────────────────────────────────────────┤
│ AGENTS 8 ▪ ACTIVE 5 ▪ FINDINGS 23 ▪ RETRIES 2 ▪ $0.14 ▪ SEQ 218      │  ← counters, 36px
├───────────────────────────────────────────┬──────────────────────────┤
│  RACK                                     │  FINDINGS                │
│                                           │                          │
│  ▸ w1  CC-4100 Payroll    ▓▓▓▓▓▒░░  work  │  ┌ HIGH ───────── w3 ─┐  │
│  ▸ w2  CC-4200 Facilities ▓▓▓▓▓▓▓▓  ✓ ok  │  │ <title>            │  │
│    └ w2·r1 amended        ▓▓▒░░░░░  work  │  │ <summary>     0.86 │  │
│  ▸ w3  CC-4310 IT         ▓▓▒░░░░░  think │  └────────────────────┘  │
│  ▸ w4  CC-4400 Court Ops  ▓░░░░░░░  block │  ┌ MED ─────────── w1 ─┐  │
│  ▸ w5  ...                                │  │ ...                │  │
│                                           │      ↑ newest on top    │
│                              60% width    │        40% width        │
├───────────────────────────────────────────┴──────────────────────────┤
│ REDUCE  ▓▓▓▓▓▓▓▓▓▓▓▓░░░  synthesizing 23 findings → brief.md         │  ← 72px
└──────────────────────────────────────────────────────────────────────┘
```

CSS Grid, three rows (`64px 36px 1fr 72px`), main row split 60/40. Fixed viewport, **no page
scroll** — if content overflows, the panes scroll internally. A demo that requires you to scroll is
a demo you've lost control of.

---

## The strip (signature element)

Each agent strip is 56px tall, `--rack` background, 3px left border in its state colour.

```
│▌ w3   CC-4310 IT Services          ▓▓▓▓▓▒░░░░░░   THINKING     4 ▪ $0.02 │
 │  │    │                            │              │            │
 │  │    │                            │              │            └ findings, cost
 │  │    │                            │              └ state (display face, uppercase)
 │  │    │                            └ work trace (see below)
 │  │    └ task title (display, 22px)
 │  └ agent id (mono, dim)
 └ state border, 3px
```

**No per-strip elapsed timer.** It would have to tick between events, and the only clock available
to a pure fold is the log's own `ts`. A wall-clock timer inside the renderer breaks replay, which
is the one thing worth protecting. The run clock in the rail advances on event timestamps; the work
trace is what carries liveness between them.

### The work trace

The one piece of real craft. Not a progress bar — you don't know progress, and a fake one is a lie
the audience can smell. It's a **live activity trace**: a 140px strip of ~28 vertical bars where a
new bar is pushed on every event that agent emits, oldest scrolling off the left.

- Bar height = a small deterministic hash of the event type, so it looks like signal rather than
  noise but is identical on replay
- Colour = `--signal` for the newest 3 bars, fading to `--dim` across the tail
- When an agent is idle, the trace holds still. When it's working, it moves.

Eight of these running side by side at different rhythms is the single most convincing "these are
genuinely parallel" cue on the screen, and it costs about 30 lines of code.

### Strip states

| State | Border | Trace | Motion |
|---|---|---|---|
| `spawning` | `--signal` | empty | slides in from left, 220ms `cubic-bezier(.2,.8,.2,1)`, staggered 60ms per strip |
| `thinking` | `--signal` @ 60% | slow drift | border opacity breathes, 2s cycle |
| `working` | `--signal` | active | trace pushes bars |
| `blocked` | `--urgent` | frozen | 1px horizontal jitter, 3s cycle — reads as *stuck*, not broken |
| `done ok` | `--verified` | freezes, desaturates | settles 4px down, dims to 70% |
| `done failed` | `--fault` | freezes red | 2-frame shake, then holds full opacity — failures stay loud |
| `retry (child)` | `--signal` | fresh | indents 28px, draws an L-bracket up to parent, slides in |

**Entry animations fire once.** The DOM is keyed by agent id and mutated in place — strips are
created on first sight and updated after that. Rebuilding `innerHTML` on every poll restarts every
CSS animation on every event, which at a 250ms tick means the entire rack slides in from the left
four times a second and the reduce bar can never transition. The `slide-in` lives on a transient
`.enter` class that is removed on `animationend`, so state changes swap the steady-state animation
(breathe, jitter, shake) without re-triggering the arrival.

Retry nesting is the loop beat. Make the bracket and the indent unmistakable from the back of the
room — that's the moment you'll be pointing at.

---

## Findings feed

Newest on top, slide-in from the right (180ms), older items compress to a single line after five
new arrivals so the pane never scrolls during a 60s run.

Each finding: severity chip (display face, uppercase, coloured), source agent id (mono, dim), title
(body 15px), summary (body 13px, clamped to two lines), confidence right-aligned (mono).

High severity gets a 2px `--urgent` left border and arrives with a 400ms glow that decays. Use it
sparingly — if everything is high, nothing is.

---

## Always-on idle state

Between runs the board must never look dead. When no agent is active and the watcher is armed:

- A slow `--signal` scanline sweeps the rack left to right, 6s, 8% opacity
- Bottom rail replaces the reduce bar with: `LISTENING · runs/inbox · 3 files seen · armed 00:41`
- The live dot in the header slow-pulses instead of holding solid

On `watch.triggered`, the whole rack flashes once at 12% amber for 200ms, then strips start
blooming. That flash is the beat that sells "always-on" — it's the board reacting *before* you
say anything.

---

## Renderer contract

```js
// The entire architecture in four lines.
let state = initialState();
for (const event of newEvents) state = apply(state, event);
render(state);
```

`apply` is pure. No fetches inside it, no `Date.now()`, no randomness that isn't seeded off
`event.seq`. That purity is what makes replay pixel-identical to live — and replay is your parachute.

### Transport

Poll, don't stream. WebSockets are a tomorrow-you problem.

```js
const res = await fetch(LOG_URL, { cache: "no-store" });
const lines = (await res.text()).split("\n").filter(Boolean);
const fresh = lines.map(JSON.parse).filter(e => e.seq > lastSeq);
```

250ms interval. Refetching a 200KB file four times a second from localhost is free. Ignore anything
with `v !== 1`, and never assume the file only grows at the end — just filter on `seq`.

**Dedupe on `seq` within a run, and watch `run_id`.** A dispatcher that restarts into the same
file writes a new `run_id` with `seq` back at 0. Deduping on `seq` alone silently discards every
event of the new run: the board keeps showing the old one and looks completely healthy while your
live run produces nothing. The renderer takes the `run_id` of the newest line as the active run and
resets state when it changes.

### Modes

| URL | Behaviour |
|---|---|
| `dashboard.html` | Live. Polls `runs/current/events.jsonl` |
| `?replay=logs/golden.jsonl` | Replays a saved log, honouring inter-event `ts` gaps. `&speed=N` divides them — but the log is paced for the script, so demo at speed 1. |
| `?big=1` | +20% type scale for projectors |
| `?seed=1` | Renders the golden log instantly with no animation — for screenshots |
| `?from=<seq>` | Seek. Folds everything below `<seq>` instantly, animates from there. This is what makes "the live run died, switch to the replay tab and pick up at the same beat" actually possible — without it replay always restarts at the bloom. |

Build replay mode **at the same time** as live mode, not after. It's ten lines if you do it now and
a panic at minute 85 if you don't.

---

## Quality floor

- Test at 1280×720 and 1920×1080. Assume the projector clips edges — 32px minimum outer padding.
- `prefers-reduced-motion`: kill the traces and transitions, keep the state colours.
- Fonts are embedded in `dashboard.html` as base64 woff2 (latin + latin-ext), not linked from a
  CDN. ~400KB, and the board renders identically with the network unplugged — verified with every
  external host blocked. Do not reintroduce the `<link>`.
- No thin light-grey text. Projectors eat it. Minimum contrast is `--dim` on `--hangar`, and check
  it from six feet back before you ship.
- Empty state: `NO RUN LOADED — start a run or open ?replay=`. An empty screen is an instruction,
  not a void.
