# 05 — Demo Script

Three minutes. Five beats. Memorize the first line and the last line; improvise the middle.

**Setup before you're called:** board open on the empty state, terminal ready with the run command
typed but not entered, trigger file on the desktop one drag from the inbox, replay tab open behind
the live tab.

---

## Beat 1 · The frame (20s)

Board is empty. Don't touch anything yet.

> "Everyone in this room built an agent swarm today. So did we. The difference is you can watch
> ours run.
>
> Right now a swarm is terminal scrollback — it scrolls past faster than you can read, it's
> interleaved from eight agents at once, and you find out what happened after it's over. You can't
> debug what you can't see. You can't sell what you can't show. So we built the board."

Then hit enter.

---

## Beat 2 · The bloom (45s) — **say nothing**

Strips slide into the rack, one after another. Traces start moving at different rhythms. Findings
begin stacking in the right pane.

**Stay quiet for at least ten seconds.** This is the hardest instruction in this document and the
most important one. The silence is what makes the room actually look at the screen. If you narrate
over the bloom, it becomes a slide with a voiceover.

When you do speak, name only what's on screen:

> "Eight agents. Each owns one slice. Nobody's waiting on anybody."

---

## Beat 3 · The failure (30s)

Point at the strip that turns red.

> "That agent made a claim its evidence doesn't support. The verifier caught it —"

The retry strip slides in nested beneath it.

> "— and it's already re-running as an amended task. There's a hard cap of three retries, so this
> terminates whether or not the model cooperates. That's the difference between a loop and a
> runaway."

The retry goes green.

Say the budget cap line out loud even though it's on screen. It's the sentence that separates a
demo from something someone would actually run, and it's the one an engineer in the room will
respect.

---

## Beat 4 · The collapse (30s)

Reducer strip runs. Headline renders in the bottom rail.

> "Everything on that board just collapsed into one brief. Eight parallel investigations,
> ninety seconds, one answer — and every line of it traces back to a specific finding from a
> specific agent against specific evidence."

Open `brief.md` for two seconds. Don't read it aloud. Let them see it exists and close it.

---

## Beat 5 · The wake-up (25s) — the closer

While they're still looking at the brief, walk over and drag the file into the inbox folder.
Then step back and put your hands down.

The rack flashes amber. Strips start blooming again.

> "That's it running always-on. It was listening the whole time."

**Then stop talking and sit down.**

Do not add a summary slide. Do not say "so in conclusion." Do not thank the judges. The board
moving by itself while you're silent and seated is the strongest possible last frame, and every
additional word makes it weaker.

---

## Timing

| Beat | Target | Cumulative |
|---|---|---|
| Frame | 0:20 | 0:20 |
| Bloom | 0:45 | 1:05 |
| Failure | 0:30 | 1:35 |
| Collapse | 0:30 | 2:05 |
| Wake-up | 0:25 | 2:30 |
| Buffer | 0:30 | 3:00 |

The buffer is real. Live runs vary. If you're at 2:50 when the reducer finishes, cut Beat 5's
setup line and just do the drag.

---

## Failure modes on stage

| What happens | What you do |
|---|---|
| Run dies mid-demo | "Here's the run from ten minutes ago." Switch tabs. Continue at the same beat. Do not debug on stage, ever. |
| Nothing turns red | Skip Beat 3 entirely. Go straight to the collapse. Nobody knows what you planned. |
| Runs long | Cut Beat 3. It's the most compressible. |
| Watcher doesn't fire | "It's also watching that folder — that's the always-on piece." Move on. Never repeat a failed live action. |
| Projector mangles it | `?big=1`, and stand closer to the screen so you're pointing at things. |

The rule underneath all of these: **never repeat a live action that failed.** One failed attempt is
a glitch. Two is the demo.

---

## If they ask questions

**"Is the board doing anything, or just displaying?"**
Just displaying — deliberately. It's a pure function of an append-only event log. Which is why it
replays exactly, why it works with any agent framework, and why adding it to your swarm is one
function call.

**"How would this run in production?"**
The log is the audit trail. Every finding has an agent, a timestamp, a confidence, and an evidence
pointer. That's most of what a control function asks for when they want to put an agent workflow
anywhere near a real process.

**"What was hard?"**
Ordering. Eight parallel writers, millisecond timestamp collisions. Solved it by funnelling through
a single sequence allocator so the renderer gets a total order it can trust — which is also what
makes replay exact.

**"What would you build next?"**
Time-travel scrubber on the log — drag back to any `seq` and see the board's exact state at that
moment. The architecture already supports it; it's a slider and a re-fold.

Keep every answer under fifteen seconds. Short answers read as confidence.
