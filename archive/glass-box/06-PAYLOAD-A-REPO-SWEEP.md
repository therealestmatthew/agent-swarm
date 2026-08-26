# 06 — Payload A: Repo Risk Sweep

**Mission statement (use this verbatim in prompts):**

> Eight specialists review the same codebase simultaneously, each through one lens. Produce a
> risk brief a tech lead could act on in thirty seconds.

**Why this payload:** zero seeding cost (the starter repo *is* the data), exact evidence refs
(`file:line`), and a mechanical verifier. The board carries the wow; the payload's only job is to be
risk-free and evidence-rich.

**Hard constraint: everything below is offline.** No package registries, no CVE lookups, no network
calls of any kind. Venue wifi plus rate limits at T+40 is a demo you lose.

---

## The eight lenses

Slice by **lens, not by directory.** Eight agents reading the same code through different eyes is a
fundamentally different picture from eight agents each grinding a folder — and on the rack, strips
labelled SECRETS / VALIDATION / TEST COVERAGE read instantly from the back of the room.

| id | Lens | Hunting for | Evidence |
|---|---|---|---|
| w1 | **SECRETS** | Hardcoded keys, tokens, connection strings, credentials in logs or fixtures | `file:line` of the literal |
| w2 | **VALIDATION** | Untrusted input reaching a sink — file paths, subprocess, SQL, deserialization — without checks | `file:line` of the sink + where input enters |
| w3 | **ERROR PATHS** | Swallowed exceptions, bare `except`, silent failure, missing cleanup on the error branch | `file:line` of the handler |
| w4 | **DEPENDENCIES** | Declared-but-unused, imported-but-undeclared, unpinned versions, deprecated API usage | `file:line` in the manifest + the import site |
| w5 | **TEST COVERAGE** | Critical paths with no test, assertions that can't fail, skipped or always-true tests | `file:line` of the untested function + absence in the test tree |
| w6 | **CONCURRENCY** | Shared mutable state across tasks, unawaited coroutines, unguarded file writes, missing timeouts | `file:line` of the shared access |
| w7 | **DOCS DRIFT** | README, docstrings, or comments that contradict the code — wrong defaults, renamed flags, stale signatures | both `file:line`s, the claim and the code |
| w8 | **DEAD WEIGHT** | Unreachable branches, unused exports, duplicated logic, TODOs older than their surrounding file | `file:line` of the dead region |

**w4 is the trap.** Dependency analysis wants to phone home. It must not. Restrict it to
manifest-versus-imports reconciliation and deprecated-API patterns visible in the source. Write that
restriction into the prompt explicitly — models reach for the network when a lens smells like
supply chain.

**If the repo is small** (under ~30 files), drop to six lenses — cut DEAD WEIGHT and CONCURRENCY.
Eight agents on a tiny repo produce eight variations of the same finding, and duplicate findings
across strips look like a bug even when they aren't.

---

## Worker prompt (filled)

```
You are worker {agent_id}, one of 8 agents reviewing the same codebase in parallel.

MISSION
Eight specialists review the same codebase simultaneously, each through one lens.
Produce a risk brief a tech lead could act on in thirty seconds.

YOUR LENS: {lens_name}
{lens_description}

You own this lens only. Another agent owns every other category. If you notice something
outside your lens, ignore it — it is already covered, and duplicate findings across agents
make the run look broken.

SCOPE
{repo_path}, excluding: .git, node_modules, .venv, dist, build, lockfiles.
Read broadly, then go deep on the 3-5 places most likely to hold real risk.
You have {time_budget} seconds. Breadth first, depth second.

NO NETWORK. Everything you need is on disk. Do not fetch, curl, pip, or npm anything.

WHAT COUNTS AS A FINDING
Something a tech lead would act on this week. Not a style preference, not a suggestion to
add types, not "consider refactoring". If your lens is clean, produce zero findings and say
so — a padded finding is worse than an empty lens.

OUTPUT
Append one line per finding to {outbox_path}:

{"type":"finding.written","payload":{"finding_id":"{agent_id}-<slug>","title":"<8 words max>",
"severity":"high|medium|low","confidence":0.0-1.0,"summary":"<25 words max>",
"evidence_ref":"<path>:<line>"}}

RULES
- evidence_ref must be a real path and a real line number in this repo. Open the file and
  confirm the line before you write it. A finding whose evidence does not check out will be
  rejected by verification and re-run, which costs the whole swarm time.
- Claim only what that line shows. "This endpoint is unauthenticated" needs the line proving
  it, not a line that merely suggests it.
- severity: high = exploitable or data-losing; medium = will bite in production;
  low = should fix, no urgency.
- confidence is honest calibration, not advocacy.
- title is read on a wall display from six feet. Front-load the noun: "Hardcoded API key in
  test fixture", not "There appears to be a potential issue with...".

Emit agent.status when you change phase: thinking -> working -> waiting.
```

---

## Verifier prompt (filled)

Mechanical on purpose. The failure has to be legible from the back of the room, not clever.

```
You are the verifier. For each finding, check exactly one thing:
open evidence_ref and confirm that line supports the claim in summary.

You are not judging whether the finding is important, well-written, or worth fixing.
Only whether the cited line is real and says what the finding claims it says.

FINDINGS
{findings_json}

Emit one line per finding:
{"type":"verify.passed","payload":{"finding_id":"...","attempt":{n}}}
{"type":"verify.failed","payload":{"finding_id":"...","attempt":{n},"reason":"<12 words max>"}}

reason must name the specific defect, one of:
- "file not found at evidence_ref"
- "line number out of range"
- "cited line does not contain the claimed pattern"
- "claim broader than the cited evidence"
- "evidence contradicts the claim"

Do not fail a finding for being minor. Only for being unsupported.
```

The first three failure reasons are decidable by opening a file — which is exactly why this payload
was chosen over the contract or spec variants, where "does this support the claim" is a judgement
call and the loop beat gets mushy.

---

## Guaranteeing the failure beat

You cannot plant a defect in a repo you receive at T+0. So bring the plant with you.

**`plant/ARCHITECTURE.md`** — write it tonight. A short, confident architecture note describing
behaviour the starter repo will not have: a retry policy with specific backoff numbers, a config
flag that doesn't exist, a default value stated wrongly. Drop it into the repo root at T+5 as
"documentation we were given."

What happens: **w7 DOCS DRIFT** reads it, finds contradictions, and writes findings citing both the
doc line and the code. At least one will overreach — claiming the code is wrong when the doc is the
thing that's wrong, or citing a line that only partly supports the claim. That trips
`claim broader than the cited evidence`, and you get the red strip.

Two backups, in order:
1. **Loosen one lens.** Give w8 DEAD WEIGHT a slightly permissive evidence instruction. Findings
   about unreachable code are the easiest to overreach on — a branch that *looks* dead usually has
   one caller somewhere.
2. **Hand-inject.** Append one `finding.written` with a deliberately bogus `evidence_ref` to the
   worker outbox before verification runs. Ten seconds of work, guarantees the beat.

**Say it in Beat 3, unprompted — do not wait to be asked.** One clause is enough: *"we seeded a
document we knew would trip it, because hoping a model makes a checkable mistake inside ninety
seconds isn't a plan."* The verification mechanism is real and running; you guaranteed it gets
exercised. Disclosed upfront that reads as method. Extracted under questioning it reads as damage
control, and the difference is entirely about who says it first.

---

## Reducer prompt (filled)

```
You are the reducer. Eight specialists reviewed this codebase in parallel, each through one
lens. Their verified findings are below.

VERIFIED FINDINGS
{findings_json}

REJECTED BY VERIFICATION: {rejected_count}

Produce exactly this:

# Risk Sweep — {repo_name}
**Headline:** one sentence a tech lead acts on.

## What we found
3-5 bullets, most consequential first. Each cites its finding_id and file:line.

## What we'd need to confirm
2-3 bullets on the weakest findings. Name them plainly, including anything verification
rejected and why.

## Coverage
One line: lenses run, findings raised, findings rejected, files touched.

Write for someone with 30 seconds. No preamble. No restating the mission. No hedging
language. Where two lenses found the same underlying issue, merge them and say both lenses
caught it — that agreement is signal.
```

Write to `runs/current/brief.md`, emit `reduce.finished {artifact_path, headline}`. The headline
renders at 22px in the bottom rail and is the last thing on screen before questions — so it has to
be a real sentence, not a label.

---

## Slice map for the dispatcher

```python
LENSES = [
    ("w1", "SECRETS",      "Hardcoded keys, tokens, connection strings, credentials in logs or fixtures."),
    ("w2", "VALIDATION",   "Untrusted input reaching a sink (path, subprocess, SQL, deserialization) unchecked."),
    ("w3", "ERROR PATHS",  "Swallowed exceptions, bare except, silent failure, missing cleanup on error branches."),
    ("w4", "DEPENDENCIES", "Manifest vs imports only — declared-unused, imported-undeclared, unpinned, deprecated APIs. NO NETWORK."),
    ("w5", "TEST COVERAGE","Critical paths with no test, assertions that cannot fail, skipped or always-true tests."),
    ("w6", "CONCURRENCY",  "Shared mutable state across tasks, unawaited coroutines, unguarded writes, missing timeouts."),
    ("w7", "DOCS DRIFT",   "README, docstrings, comments contradicting code — wrong defaults, renamed flags, stale signatures."),
    ("w8", "DEAD WEIGHT",  "Unreachable branches, unused exports, duplicated logic, TODOs older than their file."),
]
```

Strip labels on the rack are the lens names, uppercase, in the display face. That's the whole
visual story of "one codebase, eight simultaneous perspectives" and it costs you nothing.
