#!/usr/bin/env python3
"""Find every place this repo asserts a count in prose, and deterministically fix it when the
real number has drifted -- the exact failure this exists to prevent: `AGENTIC_ARCHITECTURE_MANIFEST.md`
said "48 tracked files" the moment it was itself committed and the true count became 49.

    python3 scripts/sync_counts.py            # fix mode: rewrite any drifted count in place
    python3 scripts/sync_counts.py --check     # report only, exit 1 if anything has drifted

Each entry in REGISTRY names one true count, how to compute it, and every place in the repo
that asserts it in prose. A target whose pattern doesn't match at all is reported as a warning
in both modes and as a failure in --check -- the assertion may have been reworded out from
under the pattern, which is worse than a stale number: it means this script silently stopped
tracking it.

**Scope, deliberately:** only counts about the *current, live* state of `design/plans/` and the repo
root. Numeric claims inside `archive/glass-box/` describe a specific frozen run or dataset (96
events, 338 rows, a golden log that will never regenerate differently) -- those are historical
record, not a moving target, and this script never touches that directory.

**Convention this depends on:** a trackable count is always written as a digit in the docs, never
spelled out ("7 companion files", not "seven"). A spelled-out number reads as a fixed historical
fact no script is tracking; a digit is a promise that this registry is keeping it honest.
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter as fm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


class Target(NamedTuple):
    path: Path
    pattern: re.Pattern  # exactly one capturing group, around the digits to replace


class Count(NamedTuple):
    name: str
    compute: Callable[[], int]
    targets: list[Target]


def glossary_term_count() -> int:
    text = (ROOT / "design" / "plans" / "agentic_sdlc_glossary.md").read_text(encoding="utf-8")
    return len(re.findall(r"^## .+$", text, re.M))


def glossary_category_count() -> int:
    text = (ROOT / "design" / "plans" / "agentic_sdlc_glossary.md").read_text(encoding="utf-8")
    categories = re.findall(r"\*\*Category:\*\* (.*?) \|", text)
    return len(set(categories))


def tracked_file_count() -> int:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return len([line for line in out.splitlines() if line])


def _v5_doc() -> str:
    return (ROOT / "design" / "plans" / "agentic-sdlc-design-v0.5.md").read_text(encoding="utf-8")


def live_principle_count() -> int:
    s = _v5_doc()
    block = s.split("## 1. Core Design Principles")[1].split("\n## 2.")[0]
    return len(re.findall(r"^\d+\.\s+\*\*", block, re.M))


def live_section_count() -> int:
    return len(re.findall(r"^## (\d+)\.", _v5_doc(), re.M))


def live_agent_roster_count() -> int:
    s = _v5_doc()
    block = s.split("## 2. Agent Roster")[1].split("\n## 3.")[0]
    rows = [
        line for line in block.splitlines()
        if line.startswith("|") and "---" not in line and "| Agent " not in line
    ]
    return len(rows)


def companion_file_count() -> int:
    """Mechanics files split out of the blueprint. Selected by front matter doc_type rather
    than by "every design/plans/*.md that isn't a design doc" -- that older rule silently counted any
    new design/plans/ document as a companion, which `implementation_roadmap.md` (doc_type: roadmap)
    is not. `runbook` is included deliberately: `structural_change_runbook.md` was split out of
    the blueprint alongside the companions and both count assertions have always included it."""
    plan_dir = ROOT / "design" / "plans"
    counted = {"companion", "runbook"}

    def is_sdlc_companion(path) -> bool:
        fields = fm.parse(path.read_text(encoding="utf-8"))[0]
        # part_of, not just doc_type: the assertion this feeds says the *blueprint's* mechanics
        # live in N companions. A companion belonging to another adapter would inflate a claim
        # about the SDLC design. The glob is non-recursive, so design/plans/optimization/ and
        # design/plans/agents/ are already excluded -- this guards a flat design/plans/ file declaring a
        # different part_of, which is otherwise indistinguishable here.
        return (fields.get("doc_type") in counted
                and fields.get("part_of") == "agentic-sdlc")

    return len([
        p for p in plan_dir.glob("*.md")
        if not p.name.startswith("agentic-sdlc-design") and is_sdlc_companion(p)
    ])


def agent_card_count() -> int:
    """One card per agent in design/plans/agents/. README.md is the index and card_schema.md is the
    schema -- neither describes an agent. types/ is a subdirectory and so is already excluded
    by the non-recursive glob. Whether each card corresponds to a real roster row is
    scripts/check_agent_cards.py's job; this only counts them."""
    cards_dir = ROOT / "design" / "plans" / "agents"
    if not cards_dir.is_dir():
        return 0
    excluded = {"README.md", "card_schema.md"}
    return len([p for p in cards_dir.glob("*.md") if p.name not in excluded])


def live_human_gate_count() -> int:
    s = _v5_doc()
    block = s.split("### 9.3 Human gates")[1].split("\n---")[0]
    return len([
        line for line in block.splitlines()
        if line.startswith("|") and "---" not in line and "| Gate " not in line
    ])


def t(rel_path: str, pattern: str) -> Target:
    return Target(ROOT / rel_path, re.compile(pattern))


REGISTRY: list[Count] = [
    Count("glossary_term_count", glossary_term_count, [
        t("CLAUDE.md", r"across the set — (\d+) terms, with Category and Tags columns"),
        t("AGENTIC_ARCHITECTURE_MANIFEST.md", r"(\d+) defined terms spanning \d+ categories"),
    ]),
    Count("glossary_category_count", glossary_category_count, [
        t("AGENTIC_ARCHITECTURE_MANIFEST.md", r"defined terms spanning (\d+) categories"),
    ]),
    Count("tracked_file_count", tracked_file_count, [
        # Was anchored on "... tracked files, spanning two projects" -- but the second project
        # (archive/glass-box/) was deleted in f2ba9fe, so the anchor phrase was itself the stale
        # claim. Re-anchored to the corrected sentence.
        t("AGENTIC_ARCHITECTURE_MANIFEST.md", r"(\d+) tracked files: the live design"),
    ]),
    Count("live_principle_count", live_principle_count, [
        t("AGENTIC_ARCHITECTURE_MANIFEST.md", r"(\d+) principles → \d+-agent roster"),
    ]),
    Count("live_section_count", live_section_count, [
        t("AGENTIC_ARCHITECTURE_MANIFEST.md", r"Markdown, (\d+) sections"),
    ]),
    Count("live_agent_roster_count", live_agent_roster_count, [
        t("AGENTIC_ARCHITECTURE_MANIFEST.md", r"(\d+)-agent roster"),
    ]),
    Count("companion_file_count", companion_file_count, [
        t("design/plans/agentic-sdlc-design-v0.5.md", r"mechanics live in (\d+) companion files"),
        t("CLAUDE.md", r"now (\d+) companion files, not five"),
        # A second assertion of the same count, in CLAUDE.md's "Where things live" preamble.
        # It read "Now 11 companion files" while the tracked one read 13: the original pattern
        # is case-sensitive, so the capital-N sentence was never managed and drifted silently
        # for two revisions. Distinct wording, so each target matches exactly one place.
        t("CLAUDE.md", r"set now holds (\d+) SDLC companion files"),
    ]),
    Count("agent_card_count", agent_card_count, [
        t("design/plans/agents/README.md", r"5 Executors = (\d+)\."),
        t("design/plans/agents/README.md", r"(\d+) agents: \d+ in"),
        t("design/plans/agent_taxonomy.md", r"23 existing agents \+ 2 proposed = \*\*(\d+) total\*\*"),
    ]),
    Count("live_human_gate_count", live_human_gate_count, [
        t("design/plans/implementation_roadmap.md", r"(\d+) human gates exist; nothing lets a human"),
    ]),
]


def apply_target(target: Target, true_value: int, check_only: bool) -> tuple[str, int | None]:
    """Returns (status, old_value). status in {'ok', 'fixed', 'no-match'}."""
    if not target.path.exists():
        return "no-match", None
    text = target.path.read_text(encoding="utf-8")
    m = target.pattern.search(text)
    if not m:
        return "no-match", None
    old = int(m.group(1))
    if old == true_value:
        return "ok", old
    if not check_only:
        start, end = m.span(1)
        new_text = text[:start] + str(true_value) + text[end:]
        target.path.write_text(new_text, encoding="utf-8")
    return "fixed", old


def main() -> int:
    check_only = "--check" in sys.argv
    fixed_files: set[str] = set()
    any_drift = False
    any_no_match = False

    for count in REGISTRY:
        true_value = count.compute()
        for target in count.targets:
            rel = str(target.path.relative_to(ROOT))
            status, old = apply_target(target, true_value, check_only)
            if status == "ok":
                print(f"  ok    {count.name:<26} {rel} = {true_value}")
            elif status == "fixed":
                any_drift = True
                verb = "would fix" if check_only else "fixed"
                print(f"  {verb:<8}{count.name:<25} {rel}: {old} -> {true_value}")
                if not check_only:
                    fixed_files.add(rel)
            else:
                any_no_match = True
                print(f"  ! no match for {count.name} in {rel} — pattern may be stale")

    if any_no_match:
        print("\nAt least one tracked pattern was not found. Either the sentence was reworded "
              "(update the pattern in scripts/sync_counts.py) or the file moved.")

    if check_only:
        return 1 if (any_drift or any_no_match) else 0

    if fixed_files:
        print("CHANGED:" + " ".join(sorted(fixed_files)))
    else:
        print("CHANGED:")
    return 1 if any_no_match else 0


if __name__ == "__main__":
    raise SystemExit(main())
