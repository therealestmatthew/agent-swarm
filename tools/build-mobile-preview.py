"""Build a standalone, phone-sized copy of the board for review on a device.

    python3 tools/build-mobile-preview.py

Takes dashboard.html + logs/golden.jsonl and emits build/glassbox-mobile.html:

  - the log is inlined, because the preview has no sibling files to fetch
  - a narrow-viewport layer stacks the panes and breaks each strip onto two lines
  - a touch control surface (play/pause, seq scrubber, speed) replaces the query
    string, which you cannot edit on a phone

dashboard.html itself is never modified — it is the demo asset and stays pristine.
The scrubber is the "time-travel" answer from 05-DEMO-SCRIPT.md's Q&A, and it is
exactly what that answer claims: a slider and a re-fold.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "glassbox-mobile.html"

MOBILE_CSS = """
/* The control bar is fixed at every width, so the board always needs room under
   it — outside the media query, or a desktop viewer loses the bottom rail. */
#board{padding-bottom:92px}

/* ── Narrow viewport ───────────────────────────────────────────────────────
   The board is designed for a projector: fixed viewport, no page scroll, two
   panes at 60/40. None of that survives a phone. Below 820px the page becomes
   one scrolling column, the rail sticks, and each strip breaks onto two lines
   so the label keeps the display face at a readable size instead of ellipsing
   away to nothing. Everything else — palette, type, states — is untouched.   */
@media (max-width:820px){
  html,body{height:auto;overflow:auto}
  #board{height:auto;min-height:100dvh;padding:14px 14px 100px}

  .rail{
    position:sticky;top:0;z-index:6;flex-wrap:wrap;gap:6px 12px;
    background:var(--hangar);padding:10px 0 12px;
  }
  .mark{font-size:26px}
  .clock{font-size:19px;margin-left:auto}
  .mission{order:9;flex-basis:100%;white-space:normal;line-height:1.35;font-size:12px}

  .counters{flex-wrap:wrap;gap:8px 18px;padding:10px 0 12px;margin-bottom:14px}

  .panes{grid-template-columns:1fr;gap:22px}
  .pane h2{padding-bottom:8px}
  .scroll{overflow:visible;min-height:0}

  /* Two lines: id + label + state, then trace + counts. ::after is a zero-height
     flex item that forces the wrap; .child::before is absolutely positioned and
     so is not a flex item, which leaves the retry bracket intact. */
  .strip{height:auto;flex-wrap:wrap;gap:2px 10px;padding:9px 12px 8px 15px;margin-bottom:6px}
  .strip::after{content:"";order:4;flex-basis:100%;height:0}
  .strip .id{order:1;width:auto;min-width:34px}
  .strip .label{order:2;flex:1 1 auto;min-width:0;font-size:19px}
  .strip .state{order:3;width:auto;margin-left:auto}
  .strip .trace{order:5;width:auto;flex:1 1 auto;height:16px;align-self:flex-end}
  .strip .meta{order:6;width:auto;margin-left:auto}
  .strip.child{margin-left:20px}

  .finding .sum{-webkit-line-clamp:3}
  .finding.collapsed .sum{display:none}

  .foot{flex-wrap:wrap;gap:10px 14px;min-height:0;margin-top:22px}
  #footmain{flex-wrap:wrap;gap:8px 14px}
  .foot .headline{font-size:19px}
  #footnote{max-width:100%}
}

/* ── Control surface ───────────────────────────────────────────────────────
   You cannot edit a query string on a phone, so the modes that live in the URL
   get real controls. The scrubber re-folds from initialState() on every input —
   which is the whole implementation of the time-travel answer in the Q&A.     */
#controls{
  position:fixed;left:0;right:0;bottom:0;z-index:20;
  display:flex;align-items:center;gap:12px;
  padding:11px 16px calc(11px + env(safe-area-inset-bottom));
  background:rgba(16,26,43,.94);border-top:1px solid var(--rule);
  backdrop-filter:blur(8px);
}
#controls button{
  font-family:var(--display);font-weight:600;font-size:12px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--dim);background:transparent;
  border:1px solid var(--rule);padding:8px 11px;cursor:pointer;flex:none;
  min-height:38px;
}
#controls button:hover{color:var(--chalk)}
#controls button[aria-pressed="true"]{color:var(--hangar);background:var(--signal);border-color:var(--signal)}
#controls button:focus-visible{outline:2px solid var(--signal);outline-offset:2px}
#playpause{min-width:74px;color:var(--signal);border-color:var(--signal)}
.speeds{display:flex;gap:6px;flex:none}
.speeds button{padding:8px 9px;letter-spacing:.06em}
#scrubwrap{flex:1;display:flex;align-items:center;gap:10px;min-width:0}
#scrub{
  flex:1;min-width:0;-webkit-appearance:none;appearance:none;height:34px;
  background:transparent;cursor:pointer;
}
#scrub::-webkit-slider-runnable-track{height:3px;background:var(--rule)}
#scrub::-moz-range-track{height:3px;background:var(--rule)}
#scrub::-webkit-slider-thumb{
  -webkit-appearance:none;appearance:none;width:15px;height:15px;border-radius:50%;
  background:var(--signal);margin-top:-6px;border:none;
}
#scrub::-moz-range-thumb{width:15px;height:15px;border-radius:50%;background:var(--signal);border:none}
#scrub:focus-visible{outline:2px solid var(--signal);outline-offset:4px}
#scrubval{
  font-family:var(--data);font-size:12px;color:var(--dim);flex:none;
  font-variant-numeric:tabular-nums;min-width:58px;text-align:right;
}
@media (max-width:600px){
  #controls{flex-wrap:wrap;gap:9px 10px;padding-top:9px}
  #scrubwrap{order:1;flex-basis:100%}
  .speeds{margin-left:auto}
}
"""

CONTROLS_HTML = """
<div id="controls">
  <button id="playpause" type="button">Pause</button>
  <div id="scrubwrap">
    <input id="scrub" type="range" min="0" max="0" value="0" step="1" aria-label="Event position">
    <output id="scrubval" for="scrub">0/0</output>
  </div>
  <div class="speeds" role="group" aria-label="Playback speed">
    <button type="button" data-speed="1" aria-pressed="true">1&times;</button>
    <button type="button" data-speed="2" aria-pressed="false">2&times;</button>
    <button type="button" data-speed="4" aria-pressed="false">4&times;</button>
  </div>
</div>
"""

CONTROLLER_JS = """
/* ══ Preview controller ═══════════════════════════════════════════════════
   Drives the board from the inlined log. Scrubbing re-folds from
   initialState() rather than keeping snapshots, because apply() mutates its
   accumulator — see 01-EVENT-SCHEMA.md §Test.                              */

const EVENTS = parseLines(INLINE_LOG);
const LAST = EVENTS.length;
const T0 = EVENTS.length ? Date.parse(EVENTS[0].ts) : 0;

let st = initialState();
let idx = 0;                 // number of events folded so far
let playing = true;
let speed = 1;
let baseVirtual = 0;         // virtual ms already elapsed at the last rebase
let started = performance.now();

const scrub = document.getElementById("scrub");
const scrubval = document.getElementById("scrubval");
const playBtn = document.getElementById("playpause");
scrub.max = String(LAST);

function syncUI(){
  if (scrub.value !== String(idx)) scrub.value = String(idx);
  const label = idx + "/" + LAST;
  if (scrubval.textContent !== label) scrubval.textContent = label;
  const want = playing ? "Pause" : (idx >= LAST ? "Replay" : "Play");
  if (playBtn.textContent !== want) playBtn.textContent = want;
}

function virtualNow(){ return baseVirtual + (performance.now() - started) * speed; }

function rebase(v){ baseVirtual = v; started = performance.now(); }

function foldTo(n){
  resetRender();
  st = initialState();
  for (let i = 0; i < n; i++) st = apply(st, EVENTS[i]);
  idx = n;
  render(st, "replay");
  rebase(n > 0 ? Date.parse(EVENTS[n - 1].ts) - T0 : 0);
  syncUI();
}

function tick(){
  if (playing && idx < LAST){
    const virtual = virtualNow();
    let advanced = false;
    while (idx < LAST && (Date.parse(EVENTS[idx].ts) - T0) <= virtual){
      st = apply(st, EVENTS[idx++]); advanced = true;
    }
    if (advanced){ render(st, "replay"); syncUI(); }
    if (idx >= LAST){ playing = false; syncUI(); }
  }
  requestAnimationFrame(tick);
}

playBtn.addEventListener("click", () => {
  if (idx >= LAST){ foldTo(0); playing = true; }
  else { playing = !playing; if (playing) rebase(virtualNow()); }
  syncUI();
});

scrub.addEventListener("input", () => { playing = false; foldTo(Number(scrub.value)); });

for (const b of document.querySelectorAll(".speeds button")){
  b.addEventListener("click", () => {
    rebase(virtualNow());                       // hold position across the change
    speed = Number(b.dataset.speed);
    for (const o of document.querySelectorAll(".speeds button"))
      o.setAttribute("aria-pressed", String(o === b));
  });
}

render(st, "replay");
syncUI();
requestAnimationFrame(tick);
"""


def main() -> None:
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    log = (ROOT / "logs" / "golden.jsonl").read_text(encoding="utf-8")

    styles = re.findall(r"<style>.*?</style>", html, re.S)
    if len(styles) != 2:
        raise SystemExit(f"expected 2 <style> blocks in dashboard.html, found {len(styles)}")
    body = re.search(r"<body>\n(.*)\n</body>", html, re.S).group(1)
    script_open = body.index("<script>")
    markup, script = body[:script_open], body[script_open:]

    # The board's own bootstrap fetches a run directory that does not exist here.
    bootstrap = "if (REPLAY) runReplay(); else runLive();"
    if bootstrap not in script:
        raise SystemExit("bootstrap line not found — dashboard.html changed shape")
    script = script.replace(
        bootstrap,
        f"const INLINE_LOG = {json.dumps(log)};\n{CONTROLLER_JS}",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        # <title> must come first: only the first 8KB is scanned for it, and the
        # embedded fonts are ~400KB.
        # No <head> of our own, but two metas have to travel with the page. Without
        # the charset the separators and em dashes render as mojibake wherever the
        # host does not declare UTF-8; both must land in the first 1024 bytes.
        '<meta charset="utf-8">\n'
        # Without the viewport meta:
        # without it a phone lays out at 980px, the media query never fires, and the
        # projector layout gets scaled down to something unreadable. Browsers honour
        # a viewport meta wherever they find it.
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Glass Box</title>\n"
        + styles[0] + "\n"
        + styles[1] + "\n"
        + f"<style>{MOBILE_CSS}</style>\n"
        + markup + CONTROLS_HTML + script + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1024:.0f} KB, {len(log.splitlines())} events inlined)")


if __name__ == "__main__":
    main()
