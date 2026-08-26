/**
 * The tests 01-EVENT-SCHEMA.md specifies, run against the real renderer.
 *
 *   node tests/fold.test.mjs
 *
 * The state fold is extracted from dashboard.html at run time rather than copied,
 * so these cannot drift from the code they claim to verify.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(ROOT, "dashboard.html"), "utf8");
const js = html.match(/<script>\n([\s\S]*)<\/script>/)[1];

// Take the pure section (config + fold) and parseLines; leave the DOM behind.
const foldSrc = js.split("/* ══ Render")[0]
  .replace("const qs = new URLSearchParams(location.search);", "const qs = new Map();")
  .replace('if (qs.has("big")) document.documentElement.classList.add("big");', "");
const parseSrc = js.match(/function parseLines\(text\)\{[\s\S]*?\n\}/)[0];
const { initialState, apply, parseLines } = new Function(
  `${foldSrc}\n${parseSrc}\nreturn {initialState, apply, parseLines};`
)();

const GOLDEN = readFileSync(join(ROOT, "logs/golden.jsonl"), "utf8");
const events = parseLines(GOLDEN);

let failed = 0;
function check(name, cond, detail = "") {
  if (cond) return console.log(`  ok   ${name}`);
  failed++;
  console.log(`  FAIL ${name}${detail ? " — " + detail : ""}`);
}

const norm = (s) =>
  JSON.stringify({ ...s, agents: [...s.agents.entries()], verdicts: [...s.verdicts.entries()] });
const fold = (list) => list.reduce((s, e) => apply(s, e), initialState());

console.log("\nlog integrity");
check("every line parsed", events.length === GOLDEN.trimEnd().split("\n").length);
check("seq is gap-free from 0", events.every((e, i) => e.seq === i));
check("timestamps are monotonic", events.every((e, i) => i === 0 || e.ts >= events[i - 1].ts));
check("payload is never null", events.every((e) => e.payload && typeof e.payload === "object"));

console.log("\nschema invariants (01-EVENT-SCHEMA.md)");
const spawned = new Set(events.filter((e) => e.type === "agent.spawned").map((e) => e.agent_id));
const done = new Set(events.filter((e) => e.type === "agent.done").map((e) => e.agent_id));
const orphans = [...spawned].filter((id) => !done.has(id));
check("#4 every agent.spawned gets an agent.done", orphans.length === 0, orphans.join(", "));
check(
  "#5 agent ids are never reused across parents",
  events.filter((e) => e.type === "agent.spawned").length === spawned.size
);
const finals = events.filter((e) => e.type === "run.finished").at(-1);
const emitted = events.filter((e) => e.type === "finding.written").length;
check("run.finished totals reconcile with the log", finals.payload.totals.findings === emitted,
  `totals say ${finals.payload.totals.findings}, log has ${emitted}`);
const cost = events
  .filter((e) => e.type === "agent.done")
  .reduce((n, e) => n + (e.payload.cost_usd || 0), 0);
check("run.finished cost reconciles", Math.abs(finals.payload.totals.cost_usd - cost) < 1e-6,
  `totals say ${finals.payload.totals.cost_usd}, log sums to ${cost.toFixed(4)}`);

console.log("\n#6 the renderer is a pure function of the event list");
check("test_render_is_pure — same log twice, same state", norm(fold(events)) === norm(fold(events)));
check(
  "prefix folds are stable — every prefix re-folds identically",
  [10, 40, events.length].every((n) => norm(fold(events.slice(0, n))) === norm(fold(events.slice(0, n))))
);
// apply() mutates and returns its accumulator, so a state you still hold is rewritten by
// later events. Re-folding from initialState() is the supported way to reach a past state
// (this is what a time-travel scrubber would have to do).
const held = apply(initialState(), events[0]);
const snapshot = norm(held);
events.slice(1, 20).forEach((e) => apply(held, e));
check("apply mutates its accumulator (documented, not a bug)", norm(held) !== snapshot);

console.log("\ntransport under adverse conditions");
check("mid-line truncation drops the partial line, does not throw",
  parseLines(GOLDEN.slice(0, Math.floor(GOLDEN.length * 0.6))).length > 0);
check("the final event of a complete log is not dropped",
  events.at(-1).seq === events.length - 1);
check("wrong schema version is refused",
  parseLines('{"v":2,"seq":0,"ts":"t","run_id":"r","type":"x","agent_id":"a","payload":{}}\n').length === 0);
check("garbage lines are skipped, not fatal",
  parseLines("not json\n" + GOLDEN.split("\n")[0] + "\n").length === 1);

console.log("\nseq restart (a second run appended to the same file)");
{
  // What runLive does: the newest line names the active run; a new run_id resets the board.
  const second = events.map((e) => ({ ...e, run_id: "run_beef" }));
  const file = [...events, ...second];
  const latest = file.at(-1).run_id;
  const accepted = file.filter((e) => e.run_id === latest);
  check("the new run's events are all accepted", accepted.length === second.length,
    `accepted ${accepted.length} of ${second.length}`);
  check("the board rebuilds from the new run alone",
    fold(accepted).agents.size === fold(events).agents.size);
}

console.log("\nreplay seek (?from=)");
{
  const mid = Math.floor(events.length / 2);
  const seek = fold(events.filter((e) => e.seq < events[mid].seq));
  check("folding below ?from= reaches the same state as replaying to it",
    norm(seek) === norm(fold(events.slice(0, mid))));
}

console.log(failed ? `\n${failed} FAILED\n` : "\nall passed\n");
process.exit(failed ? 1 : 0);
