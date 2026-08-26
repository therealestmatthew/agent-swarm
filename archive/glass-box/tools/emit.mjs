/**
 * The Glass Box emitter, in JavaScript. Paste this into the starter repo.
 *
 * 00-MASTER-PLAN.md and 04-TOMORROW-RUNBOOK.md both promise "if the repo is TypeScript,
 * the emitter is nine lines". This is that file. The contract is the file format, not the
 * library — nothing here needs to match glassbox/events.py beyond the bytes it writes.
 *
 *   import { EventLog } from "./emit.mjs";
 *   const log = new EventLog("runs/current");
 *   log.runStarted("...", 8);
 *   log.spawned("w1", "worker", "SECRETS");     // <- the WORKER's id, never "dispatch"
 *   log.status("w1", "working", "scanning");
 *   log.finding("w1", { finding_id: "w1-01", title: "...", severity: "high",
 *                       confidence: 0.9, summary: "...", evidence_ref: "src/a.py:12" });
 *   log.done("w1", { status: "ok", duration_ms: 1200, cost_usd: 0.004 });
 *   log.runFinished("ok", 90000, { findings: 17, retries: 1, cost_usd: 0.21 });
 */

import { appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

export class EventLog {
  constructor(runDir, runId) {
    this.runDir = runDir;
    this.path = join(runDir, "events.jsonl");
    this.runId = runId ?? "run_" + Math.random().toString(16).slice(2, 6);
    this.seq = 0;
    mkdirSync(runDir, { recursive: true });
  }

  /**
   * @param agentId THE AGENT THIS EVENT IS ABOUT — not whoever is writing it.
   *
   * This argument is first and required on purpose. The dispatcher is responsible for
   * emitting `agent.spawned`, but the event *describes a worker*, so it carries the
   * worker's id. Passing "dispatch" for eight spawns makes the renderer — which keys
   * agents on agent_id — overwrite one record eight times, and you get a single strip
   * instead of eight, with no error and nothing in the console.
   */
  emit(type, agentId, payload = {}, parentId = null) {
    const event = {
      v: 1,
      seq: this.seq++,
      ts: new Date().toISOString().replace(/(\.\d{3})\d*Z$/, "$1Z"),
      run_id: this.runId,
      type,
      agent_id: agentId,
      parent_id: parentId,
      payload,
    };
    // One write per event, newline-terminated: the renderer treats a trailing line with
    // no newline as a partial write and waits for the next poll.
    appendFileSync(this.path, JSON.stringify(event) + "\n");
    return event;
  }

  // -- convenience, matching glassbox/events.py --------------------------------

  runStarted(mission, plannedAgents, inputRef = "") {
    return this.emit("run.started", "dispatch", {
      mission, planned_agents: plannedAgents, input_ref: inputRef,
    });
  }

  runFinished(status, durationMs, totals) {
    return this.emit("run.finished", "dispatch", {
      status, duration_ms: durationMs, totals,
    });
  }

  spawned(agentId, role, label, model = "", parentId = null) {
    return this.emit("agent.spawned", agentId, { role, label, model }, parentId);
  }

  status(agentId, state, note = "") {
    return this.emit("agent.status", agentId, { state, note });
  }

  /** payload needs finding_id, title, severity, confidence, summary, evidence_ref. */
  finding(agentId, payload) {
    return this.emit("finding.written", agentId, payload);
  }

  done(agentId, payload) {
    return this.emit("agent.done", agentId, payload);
  }
}
