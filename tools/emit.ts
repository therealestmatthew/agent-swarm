/**
 * The Glass Box emitter, in TypeScript. Paste this into the starter repo.
 *
 * Identical contract to tools/emit.mjs and glassbox/events.py — the contract is the file
 * format, so these three only have to agree on the bytes.
 *
 *   const log = new EventLog("runs/current");
 *   log.runStarted("...", 8);
 *   log.spawned("w1", "worker", "SECRETS");     // <- the WORKER's id, never "dispatch"
 *   log.status("w1", "working", "scanning");
 *   log.finding("w1", { finding_id: "w1-01", title: "...", severity: "high",
 *                       confidence: 0.9, summary: "...", evidence_ref: "src/a.py:12" });
 *   log.done("w1", { status: "ok", duration_ms: 1200, cost_usd: 0.004 });
 */

import { appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

export type AgentRole = "worker" | "verifier" | "reducer";
export type AgentState = "thinking" | "working" | "waiting" | "blocked";
export type Severity = "high" | "medium" | "low";

export interface GlassBoxEvent {
  v: 1;
  seq: number;
  ts: string;
  run_id: string;
  type: string;
  agent_id: string;
  parent_id: string | null;
  payload: Record<string, unknown>;
}

export interface Finding {
  finding_id: string;
  title: string;
  severity: Severity;
  confidence: number;
  summary: string;
  evidence_ref: string;
}

export class EventLog {
  readonly path: string;
  readonly runId: string;
  private seq = 0;

  constructor(runDir: string, runId?: string) {
    this.path = join(runDir, "events.jsonl");
    this.runId = runId ?? "run_" + Math.random().toString(16).slice(2, 6);
    mkdirSync(runDir, { recursive: true });
  }

  /**
   * @param agentId THE AGENT THIS EVENT IS ABOUT — not whoever is writing it.
   *
   * Required and first on purpose. The dispatcher is responsible for emitting
   * `agent.spawned`, but the event *describes a worker*, so it carries the worker's id.
   * Passing "dispatch" for eight spawns makes the renderer — which keys agents on
   * agent_id — overwrite one record eight times: a single strip instead of eight, with no
   * error and nothing in the console.
   */
  emit(
    type: string,
    agentId: string,
    payload: Record<string, unknown> = {},
    parentId: string | null = null,
  ): GlassBoxEvent {
    const event: GlassBoxEvent = {
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

  runStarted(mission: string, plannedAgents: number, inputRef = ""): GlassBoxEvent {
    return this.emit("run.started", "dispatch", {
      mission, planned_agents: plannedAgents, input_ref: inputRef,
    });
  }

  runFinished(
    status: "ok" | "partial" | "failed",
    durationMs: number,
    totals: Record<string, unknown>,
  ): GlassBoxEvent {
    return this.emit("run.finished", "dispatch", { status, duration_ms: durationMs, totals });
  }

  spawned(
    agentId: string, role: AgentRole, label: string, model = "", parentId: string | null = null,
  ): GlassBoxEvent {
    return this.emit("agent.spawned", agentId, { role, label, model }, parentId);
  }

  status(agentId: string, state: AgentState, note = ""): GlassBoxEvent {
    return this.emit("agent.status", agentId, { state, note });
  }

  finding(agentId: string, finding: Finding): GlassBoxEvent {
    return this.emit("finding.written", agentId, { ...finding });
  }

  done(
    agentId: string,
    payload: { status: "ok" | "failed"; duration_ms?: number; cost_usd?: number },
  ): GlassBoxEvent {
    return this.emit("agent.done", agentId, { ...payload });
  }
}
