# 08 — Adversarial Review Prompt

Paste everything below the line into Claude Code, with all Glass Box files in the working directory.

---

## Context

I am doing a 90-minute hackathon tomorrow at an in-person Anthropic training session. The themes
are open-ended, announced only as: **agent swarms, always-on, and looping**. I receive a starter
repo at T+0 and have not seen it. After the build I get roughly three minutes to demo, and the
demo is what I'm optimizing for.

The files in this directory are my complete plan. Here's the thesis:

**Glass Box** is a live mission-control board that makes an agent swarm visible while it runs. The
bet is that every team will build a swarm and none will *show* one — swarms currently live in
terminal scrollback, invisible and interleaved. So the differentiator isn't the agents, it's the
visualization.

The architecture decouples everything through **one append-only JSONL event log**. Agents emit
events; a single-file HTML dashboard tails the log and renders it. That's supposed to buy three
things:

1. I can build the entire visual tonight against a fake emitter, with zero dependency on the
   unseen starter repo.
2. Integration tomorrow is adding `emit()` at ~5 call sites, regardless of the repo's framework.
3. The dashboard is a pure function of the event list, so replaying a saved log renders
   identically — which is my parachute if the live run dies on stage.

All three themes land in one build: swarm = fan-out to 6–8 workers; looping = a verifier that
re-dispatches failed findings as nested retry agents; always-on = a folder watcher that wakes the
same board mid-demo.

The payload is a repo risk sweep (eight lenses over the starter repo), with a budget variance hunt
as fallback.

## What I want from you

**Adversarial analysis. Not validation.** I have been working on this alone for several hours and
I am almost certainly in love with my own idea. Your job is to find the places where it breaks.

Do not tell me what's good about the plan. I know the case for it — I wrote it. Assume every
strength I've claimed is real and spend all your effort on what I've missed.

Specifically:

### 1. Attack the core bet
The entire plan rests on "nobody else will visualize their swarm, so the board is the
differentiator." Argue the other side. What if visualization reads as *presentation polish* rather
than engineering to a room of Anthropic engineers? What if it looks like I spent 90 minutes on CSS
instead of agents? Is there a version of that criticism I can't answer?

### 2. Break the architecture
Read `01-EVENT-SCHEMA.md` and `02-DASHBOARD-DESIGN.md` closely.
- Where does the "pure function of the event list" claim actually fail? Find the specific places
  where I've leaked impurity without noticing.
- The concurrency section offers two options for `seq` allocation. Is either actually safe under
  the conditions I described? What breaks at 8 parallel writers that I haven't accounted for?
- What happens to the renderer under adverse conditions I haven't considered — partial line writes,
  a log that gets truncated, events arriving with duplicate `seq`, a 50MB log?

### 3. Find the unstated dependencies
The plan claims repo-agnosticism. Enumerate every assumption it actually makes about the starter
repo — language, execution model, file system access, whether I can even run a local HTTP server on
the venue's machine, whether the repo already has its own orchestration I'd be fighting. Which of
those assumptions, if wrong, costs me more than 15 minutes?

### 4. Red-team the timeline
`04-TOMORROW-RUNBOOK.md` has checkpoints at T+15, T+45, T+60, T+75. Assume I'm slower than I think.
Which checkpoint slips first, and what's the cascade? Is the T+75 feature freeze realistic or is it
the kind of rule people write and then ignore? Where would a competent person actually lose this?

### 5. Red-team the demo
Read `05-DEMO-SCRIPT.md`. Attack it as a hostile audience member:
- What's the most damaging question someone could ask, and does my prepared answer survive it?
- The plan deliberately seeds an input that reliably triggers a verification failure, and I intend
  to be upfront about that. Is that defensible or does it undercut the whole thing?
- Beat 2 instructs me to say nothing for ten seconds. Does that read as confident or as dead air?

### 6. Check internal consistency
These files were written in sequence and may contradict each other. Cross-check the event types in
`01` against what `02` claims to render and what `03` claims to emit. Find the mismatches. Check
that the slice maps, agent ids, and prompt templates in `03`, `06`, and `07` actually agree.

### 7. The question I should have asked
What's the risk I haven't named anywhere in these eight files?

## Output format

1. **Kill shots** — anything that could make the whole approach fail. Ranked. Be specific about the
   mechanism of failure, not the category.
2. **Concrete defects** — file, section, what's wrong, what it should say instead.
3. **Cut recommendations** — given 90 minutes and my likely optimism, what should come out of the
   plan *tonight* that I'm currently planning to build?
4. **The strongest alternative** — if you think there's a better use of 90 minutes against these
   three themes, say so plainly and make the case.

Be blunt. If the idea is fundamentally weaker than I think, tell me tonight while I can still change
course, not tomorrow at T+60. A polite review is worthless to me right now.
