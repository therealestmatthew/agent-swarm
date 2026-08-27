---
title: "07 — Payload B: Budget Variance Hunt (fallback)"
status: archived
part_of: glass-box
doc_type: payload-spec
---

# 07 — Payload B: Budget Variance Hunt (fallback)

**Trigger this swap if, at T+15, any of these are true:**
- The starter repo is under ~20 files (eight lenses will produce eight versions of one finding)
- It's generated scaffolding with no real logic to review
- It's in a stack where you can't read the code fast enough to sanity-check findings live
- The room's framing turns out to be business-facing rather than engineering-facing

**Cost of the swap: one prompt file, a path, and your parachute.** The event schema, dashboard,
dispatcher, verifier mechanics, runbook, and demo script are all untouched — that's the whole point
of the architecture, the board never knew what the payload was.

> **But `logs/golden.jsonl` is Payload A end to end.** It hardcodes the eight code-review lenses,
> `ARCHITECTURE.md:21` as the seeded failure, and a headline about credentials in main. Swap at
> T+15 and your parachute shows a repo sweep while you narrate a budget audit. Regenerating means
> rewriting `FINDINGS`, `RETRY_FINDING`, `LENSES` and the reducer headline in `glassbox/simulate.py`
> — twenty minutes at exactly the moment the swap was supposed to save you time.
>
> **So decide this before T+15, not at it.** Either commit to Payload A tonight, or build the
> Payload B golden log tonight as well. What you cannot do is swap on the day and keep the
> parachute. (After T+75 the run you saved to `logs/backup-live.jsonl` is the real parachute
> anyway — but that only helps if you got that far.)

---

## Mission statement

> Eight agents audit a six-month budget-versus-actuals file in parallel, one cost center each.
> Produce a variance brief a finance director could act on in thirty seconds.

---

## The data

`fallback/budget_actuals.csv` — 338 rows, Program → Cost Center → Account → Period, six periods
across eight cost centers. `fallback/account_master.csv` is the join that makes orphan codes
mechanically detectable.

Regenerate deterministically at any time: `python3 generate_budget.py`. Same seed, same file — which
matters, because your golden log and demo narrative assume specific findings at specific rows.

### Slice map

| id | Cost center | Program |
|---|---|---|
| w1 | CC-4100 Courtroom Staffing | Criminal Operations |
| w2 | CC-4110 Case Processing | Criminal Operations |
| w3 | CC-4200 Civil Filings | Civil Operations |
| w4 | CC-4210 Small Claims | Civil Operations |
| w5 | CC-4300 Building Maintenance | Facilities |
| w6 | CC-4310 Security Services | Facilities |
| w7 | CC-4400 Infrastructure | Technology |
| w8 | CC-4410 Application Support | Technology |

Clean slicing: every agent gets 42 rows — except CC-4300 and CC-4400, which get 43, because the
planted duplicate posting and the orphan account code are extra rows. Nobody grinds while seven sit
idle. Strip labels on the rack are the cost center names.

---

## What's planted, and which agent should find it

| # | Where | What | Expect |
|---|---|---|---|
| 1 | CC-4100 · 5150 Overtime | Escalating every period: 29k budget vs 29k → 90k actual across six months | **HIGH** — w1. The cleanest trend finding in the file. |
| 2 | CC-4410 · 5700 Equipment | Budget drops to 0 in Apr–Jun, actuals continue at ~28k | **HIGH** — w8. Unbudgeted spend. |
| 3 | CC-4300 · 5400 · 2026-03 | Identical row appears twice, same actual (31,109) | **MEDIUM** — w5. Duplicate posting. |
| 4 | CC-4200 · 5600 · 2026-05 | Actual of −14,200 | **MEDIUM** — w3. Credit misposting. |
| 5 | CC-4400 · account 5999 | 67,400 against an account code absent from `account_master.csv` | **HIGH** — w7. Fails the join. |
| 6 | CC-4310 · 5400 | **The honeypot.** April at 2.9× budget, then May and June at 6% | **the failure beat** — w6 |

### On the honeypot

Verified against the generated file: April is 118,320 against a 40,800 budget, May and June are
2,448 each, and the six-period net is **+759 on a 244,800 budget — 0.3%**. The trap is real and the
adjacent periods genuinely refute the single-period claim.


April looks like a blowout: 118,320 against a 40,800 budget. An agent reading that period in
isolation will file "Security services overspent Q2 by 190%" with high confidence — and it's wrong.
May and June come in at 2,448 each. Net variance across the half-year is roughly zero. It's a
prepaid annual contract, a timing shift, not overspend.

This is your `claim broader than the cited evidence` rejection, and it's a *better* failure than the
repo payload's, because it's the mistake a real analyst makes every close cycle. The verifier's job
here is one instruction: **check the adjacent periods before accepting a single-period variance
claim.** When the retry strip comes back green with "timing difference, not overspend," you've shown
the loop catching a genuinely subtle error rather than a typo.

That's a stronger Beat 3 than anything in Payload A. Worth knowing even if you don't swap.

---

## Worker prompt (filled)

```
You are worker {agent_id}, one of 8 agents auditing the same budget file in parallel.

MISSION
Eight agents audit a six-month budget-versus-actuals file, one cost center each. Produce a
variance brief a finance director could act on in thirty seconds.

YOUR SLICE
Cost center {cost_center} ({cost_center_name}), program {program}.
Data: {data_path}. Account reference: {account_master_path}.
42 rows: 7 accounts x 6 periods, 2026-01 through 2026-06.

You own this cost center only. Seven other agents own the rest. Do not comment on theirs.

WHAT COUNTS AS A FINDING
Something a finance director acts on: overspend with a trend, unbudgeted activity, a posting
that looks like an error, spend against an invalid account. Not "actuals were 3% over budget"
— that is noise, and every cost center has it.

CHECK BEFORE YOU CLAIM
- A single period above budget is not overspend. Look at adjacent periods first. Prepayments
  and timing shifts look identical to overspend for exactly one month.
- Confirm every account code appears in the account reference file.
- Look for exact-duplicate rows before attributing a spike to real activity.
- Negative actuals are postings, not savings.

OUTPUT
Append one line per finding to {outbox_path}:

{"type":"finding.written","payload":{"finding_id":"{agent_id}-<slug>","title":"<8 words max>",
"severity":"high|medium|low","confidence":0.0-1.0,"summary":"<25 words max>",
"evidence_ref":"{cost_center}|<account>|<period>"}}

RULES
- evidence_ref names the exact row: cost center, account, period. It must exist in the file.
- Claim only what those rows show across the full six periods.
- severity: high = money is leaving without authorization or control; medium = likely error
  needing correction; low = worth a look at year-end.
- title is read on a wall display from six feet. Front-load the noun: "Overtime up 210% since
  January", not "There is a concerning trend in...".

Emit agent.status when you change phase: thinking -> working -> waiting.
```

---

## Verifier prompt (filled)

```
You are the verifier. For each finding, check exactly one thing: do the rows at evidence_ref
support the claim in summary?

FINDINGS
{findings_json}

DATA
{data_path}

Check in this order:
1. Do the rows at evidence_ref exist?
2. Do those rows show what the summary claims?
3. If the claim is about overspend in one period, do the ADJACENT periods contradict it?
   A period above budget followed by periods below budget is a timing difference, not
   overspend, and the claim is broader than its evidence.

Emit one line per finding:
{"type":"verify.passed","payload":{"finding_id":"...","attempt":{n}}}
{"type":"verify.failed","payload":{"finding_id":"...","attempt":{n},"reason":"<12 words max>"}}

reason must be one of:
- "rows not found at evidence_ref"
- "cited rows do not show the claimed pattern"
- "claim broader than the cited evidence"
- "adjacent periods contradict the claim"

Do not fail a finding for being minor. Only for being unsupported.
```

Reducer prompt: use the one in `03-AGENT-CONTRACTS.md`, retitled `# Variance Sweep — 2026 H1`. The
"where two lenses found the same issue, merge them" line becomes "where two cost centers show the
same pattern, say so — a pattern across centers is a control problem, not a local one."

---

## The line to say if you use this

> "We pointed eight agents at six months of budget data. Ninety seconds later one of them had
> flagged a 190% overspend that wasn't real — and the verifier caught it before it reached the
> brief. That's the part that decides whether you can put this near a real close process."

Better Q&A material than Payload A, and it's your home ground. The only reason it isn't the primary
is the seeding cost and the risk that an engineering room reads finance data as someone else's
problem.
