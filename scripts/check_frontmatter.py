#!/usr/bin/env python3
"""Ensure every Markdown doc in this repo has valid YAML front matter, and generate the
front-matter manifest from what it finds.

    python3 scripts/check_frontmatter.py            # fix mode: backfill/repair, then write
                                                      # FRONTMATTER_MANIFEST.md
    python3 scripts/check_frontmatter.py --check     # report only, exit 1 on anything missing

Fix mode never overwrites a field that's already present and valid -- it only fills what's
missing, so re-running this is always safe and a manual edit to front matter is never clobbered.
`superseded_by` is the one exception: it's recomputed every run from the actual file layout
(see `_version_chain`), because a hand-edited value would silently go stale the moment a newer
version lands, which is exactly the class of drift this whole exercise exists to prevent.

Doc type is looked up from CURATED_DOC_TYPES for every file that existed when this script was
written. A file not in that table gets doc_type "reference" and a printed warning -- an honest
default rather than a guessed one; set it explicitly and it will never be touched again.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import frontmatter as fm

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "FRONTMATTER_MANIFEST.md"

# Exact doc_type for every file that existed at authoring time. New files fall through to the
# path-based default in `infer_doc_type` instead of failing here.
CURATED_DOC_TYPES: dict[str, str] = {
    "CLAUDE.md": "guide",
    "AGENTIC_ARCHITECTURE_MANIFEST.md": "manifest",
    "FRONTMATTER_MANIFEST.md": "manifest",
    "plan/agentic-sdlc-design-v0.5.md": "blueprint",
    "plan/budget_and_escalation_policy.md": "companion",
    "plan/calibration_and_measurement.md": "companion",
    "plan/context_retrieval_strategy.md": "companion",
    "plan/execution_isolation.md": "companion",
    "plan/infra_triage_matrix.md": "companion",
    "plan/structural_change_runbook.md": "companion",
    "plan/test_harness_architecture.md": "companion",
    "plan/versions/REGRESSION.md": "analysis",
    "plan/versions/agentic-sdlc-design-v0.1.md": "blueprint",
    "plan/versions/agentic-sdlc-design-v0.2.md": "blueprint",
    "plan/versions/agentic-sdlc-design-v0.3.md": "blueprint",
    "plan/versions/agentic-sdlc-design-v0.4.md": "blueprint",
    "archive/glass-box/README.md": "archive-notice",
    "archive/glass-box/00-MASTER-PLAN.md": "blueprint",
    "archive/glass-box/01-EVENT-SCHEMA.md": "schema",
    "archive/glass-box/02-DASHBOARD-DESIGN.md": "design-spec",
    "archive/glass-box/03-AGENT-CONTRACTS.md": "agent-contracts",
    "archive/glass-box/04-TOMORROW-RUNBOOK.md": "runbook",
    "archive/glass-box/05-DEMO-SCRIPT.md": "demo-script",
    "archive/glass-box/06-PAYLOAD-A-REPO-SWEEP.md": "payload-spec",
    "archive/glass-box/07-PAYLOAD-B-BUDGET-FALLBACK.md": "payload-spec",
    "archive/glass-box/08-ADVERSARIAL-REVIEW-PROMPT.md": "review-prompt",
    "archive/glass-box/09-REVIEW-FINDINGS.md": "review-findings",
    "archive/glass-box/10-SECOND-PASS.md": "review-findings",
    "archive/glass-box/QUICKSTART.md": "guide",
}

VERSION_RE = re.compile(r"-v(\d+\.\d+)\.md$")


def tracked_markdown_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return sorted(ROOT / line for line in out.splitlines() if line)


def _version_chain() -> dict[str, str]:
    """Maps each superseded version's relative path to what supersedes it, computed fresh
    from the actual file layout every run -- see the module docstring for why."""
    live = None
    for p in (ROOT / "plan").glob("agentic-sdlc-design-v*.md"):
        m = VERSION_RE.search(p.name)
        if m:
            live = (m.group(1), f"plan/{p.name}")
    historical: list[tuple[str, str]] = []
    for p in (ROOT / "plan" / "versions").glob("agentic-sdlc-design-v*.md"):
        m = VERSION_RE.search(p.name)
        if m:
            historical.append((m.group(1), f"plan/versions/{p.name}"))
    historical.sort(key=lambda t: [int(x) for x in t[0].split(".")])

    chain: dict[str, str] = {}
    for i, (_version, path) in enumerate(historical):
        if i + 1 < len(historical):
            chain[path] = historical[i + 1][1]
        elif live:
            chain[path] = live[1]
    return chain


def infer_defaults(rel_path: str, body: str, superseded_by: dict[str, str]) -> dict:
    parts = Path(rel_path).parts
    if parts[0] == "archive":
        part_of, status = "glass-box", "archived"
    elif parts[0] == "plan":
        part_of = "agentic-sdlc"
        status = "superseded" if len(parts) > 1 and parts[1] == "versions" else "live"
        if rel_path == "plan/versions/REGRESSION.md":
            status = "live"  # the analysis, not a version of the blueprint itself
    else:
        part_of, status = "repo-meta", "live"

    doc_type = CURATED_DOC_TYPES.get(rel_path)
    if doc_type is None:
        doc_type = "reference"
        print(f"  ! {rel_path}: no curated doc_type, defaulting to 'reference' -- set explicitly")

    fields: dict = {"status": status, "part_of": part_of, "doc_type": doc_type}

    m = VERSION_RE.search(rel_path)
    if m:
        fields["version"] = m.group(1)
    if rel_path in superseded_by:
        fields["superseded_by"] = superseded_by[rel_path]

    title = fm.extract_title(body)
    if title:
        fields["title"] = title
    return fields


def process(path: Path, superseded_by: dict[str, str], check_only: bool) -> tuple[bool, str | None]:
    """Returns (needs_fix, error). error is set only when a doc can't be safely repaired."""
    rel = str(path.relative_to(ROOT))
    text = path.read_text(encoding="utf-8")
    fields, body, had_fm = fm.parse(text)

    defaults = infer_defaults(rel, body, superseded_by)
    merged = dict(fields)
    changed = False
    for key, value in defaults.items():
        # superseded_by is recomputed every run (see _version_chain); everything else fills
        # gaps only, never overwrites a value already present.
        if key == "superseded_by" or key not in merged or merged[key] in (None, ""):
            if merged.get(key) != value:
                merged[key] = value
                changed = True

    missing_required = [k for k in fm.REQUIRED_FIELDS if not merged.get(k)]
    if missing_required:
        if "title" in missing_required:
            return True, f"{rel}: no H1 heading found -- can't derive a title, fix manually"
        return True, f"{rel}: missing required field(s) {missing_required} with no inferable default"

    if merged.get("doc_type") not in fm.DOC_TYPES and merged.get("doc_type") != "reference":
        print(f"  ! {rel}: unrecognized doc_type '{merged['doc_type']}' (not enforced, just noting)")

    if not had_fm or changed:
        if not check_only:
            fm.rewrite(path, merged, body)
        return True, None
    return False, None


def write_manifest(rows: list[tuple[str, dict]]) -> None:
    from collections import Counter

    by_status = Counter(f.get("status", "?") for _, f in rows)
    by_part_of = Counter(f.get("part_of", "?") for _, f in rows)
    by_doc_type = Counter(f.get("doc_type", "?") for _, f in rows)

    lines = [
        "---",
        "title: Front Matter Manifest",
        "status: live",
        "part_of: repo-meta",
        "doc_type: manifest",
        "generated: true",
        "---",
        "",
        "# Front Matter Manifest",
        "",
        "**Generated by `scripts/check_frontmatter.py`. Do not hand-edit -- re-run the script "
        "instead; edits here are overwritten on the next run.**",
        "",
        f"{len(rows)} Markdown files, all with valid front matter as of the last run.",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|---|---|",
    ]
    for status in fm.STATUSES:
        lines.append(f"| {status} | {by_status.get(status, 0)} |")
    lines += ["", "| Part of | Count |", "|---|---|"]
    for part in fm.PART_OF:
        lines.append(f"| {part} | {by_part_of.get(part, 0)} |")
    lines += ["", "| Doc type | Count |", "|---|---|"]
    for doc_type, count in sorted(by_doc_type.items(), key=lambda t: -t[1]):
        lines.append(f"| {doc_type} | {count} |")

    lines += ["", "## Every file", "", "| Path | Title | Status | Part of | Doc type | Version | Supersedes |", "|---|---|---|---|---|---|---|"]
    for rel, fields in sorted(rows):
        lines.append(
            f"| `{rel}` | {fields.get('title', '')} | {fields.get('status', '')} | "
            f"{fields.get('part_of', '')} | {fields.get('doc_type', '')} | "
            f"{fields.get('version', '')} | {fields.get('superseded_by', '')} |"
        )

    MANIFEST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    check_only = "--check" in sys.argv
    files = tracked_markdown_files()
    superseded_by = _version_chain()

    changed_paths: list[str] = []
    errors: list[str] = []

    for path in files:
        if path.resolve() == MANIFEST_PATH.resolve():
            continue  # rewritten wholesale below, not patched in place
        needs_fix, error = process(path, superseded_by, check_only)
        if error:
            errors.append(error)
            continue
        if needs_fix:
            changed_paths.append(str(path.relative_to(ROOT)))

    if errors:
        print("Front matter check FAILED:")
        for e in errors:
            print(f"  ✗ {e}")
        return 1

    if changed_paths:
        print(f"Front matter backfilled/repaired on {len(changed_paths)} file(s):")
        for p in changed_paths:
            print(f"  ~ {p}")
    else:
        print("Front matter: all tracked Markdown files already valid.")

    if check_only:
        return 1 if changed_paths else 0

    fm_rows = []
    for path in files:
        if path.resolve() == MANIFEST_PATH.resolve():
            continue
        fields, _, _ = fm.parse(path.read_text(encoding="utf-8"))
        fm_rows.append((str(path.relative_to(ROOT)), fields))
    write_manifest(fm_rows)
    print(f"Wrote {MANIFEST_PATH.relative_to(ROOT)} ({len(fm_rows)} files).")

    if changed_paths:
        print("CHANGED:" + " ".join(changed_paths + ["FRONTMATTER_MANIFEST.md"]))
    else:
        print("CHANGED:" + " ".join(["FRONTMATTER_MANIFEST.md"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
