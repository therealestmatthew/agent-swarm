"""Shared front-matter parser for this repo's Markdown docs.

Stdlib only, deliberately. `pyyaml` is available in this environment, but nothing at the repo
root declares it as a dependency (there's no root `pyproject.toml`/`requirements.txt`), and
`scripts/*.py` runs inside a pre-commit hook — the one place in this repo where a missing
dependency failing silently would be worst. The front matter this repo actually uses is flat
key: value pairs plus the occasional inline list; that's a small enough grammar to parse
correctly without a general YAML parser, which is the same tradeoff
`archive/glass-box/glassbox/events.py` already made for the same reason.

Schema (see FRONTMATTER_MANIFEST.md for the live catalogue of what every doc actually has):

    title:          str,  required
    status:         "live" | "superseded" | "archived",  required
    part_of:        "agentic-sdlc" | "glass-box" | "repo-meta",  required
    doc_type:       str, required — see DOC_TYPES for the known set (unknown values warn, not fail)
    version:        str, optional — only versioned blueprint docs
    superseded_by:  str, optional — path, only on a superseded blueprint version
    generated:      bool, optional, default false — true only for files a script fully produces
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

FM_DELIM = "---"
FM_BLOCK_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)

REQUIRED_FIELDS = ("title", "status", "part_of", "doc_type")
STATUSES = ("live", "superseded", "archived")
PART_OF = ("agentic-sdlc", "glass-box", "repo-meta")
# Known doc_types. Not enforced as a hard failure -- an unrecognized value is a warning, so a
# genuinely new kind of document doesn't need this file edited before it can be committed.
DOC_TYPES = (
    "blueprint", "companion", "analysis", "glossary-notes", "guide", "manifest", "schema",
    "design-spec", "agent-contracts", "runbook", "demo-script", "payload-spec",
    "review-prompt", "review-findings", "archive-notice",
)

# Stable output order, independent of insertion order, so regenerated front matter is
# diff-stable rather than reordering itself every run.
FIELD_ORDER = (
    "title", "status", "part_of", "doc_type", "version", "superseded_by", "generated",
)


def parse(text: str) -> tuple[dict[str, Any], str, bool]:
    """Returns (fields, body, had_frontmatter). Malformed lines are skipped, not fatal --
    a doc with a typo in one line should still get its other fields read and repaired."""
    m = FM_BLOCK_RE.match(text)
    if not m:
        return {}, text, False
    block, body = m.group(1), text[m.end():]
    fields: dict[str, Any] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key, raw = key.strip(), raw.strip()
        fields[key] = _parse_scalar(raw)
    return fields, body, True


def _parse_scalar(raw: str) -> Any:
    if raw in ("true", "false"):
        return raw == "true"
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        return raw[1:-1]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(v.strip()) for v in inner.split(",")]
    return raw


_LOOKS_NUMERIC = re.compile(r"^-?\d+(\.\d+)?$")


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(_format_scalar(v) for v in value) + "]"
    s = str(value)
    # Quote whenever a real YAML parser would read this back as something other than a
    # string: a colon or bracket would corrupt the block; a bare "0.5" parses as a float,
    # and 0.10 == 0.1 as a float -- every value in this schema is meant to stay a string
    # (this project's own versions are single-digit-decimal today, but that's exactly the
    # kind of assumption that shouldn't be load-bearing here).
    if s == "" or any(c in s for c in ":#[]{}") or s[0] in "!&*-?|>%@`\"'" or _LOOKS_NUMERIC.match(s):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def serialize(fields: dict[str, Any]) -> str:
    lines = [FM_DELIM]
    seen = set()
    for key in FIELD_ORDER:
        if key in fields and fields[key] is not None:
            lines.append(f"{key}: {_format_scalar(fields[key])}")
            seen.add(key)
    # Anything outside the known schema is preserved rather than silently dropped.
    for key, value in fields.items():
        if key not in seen and value is not None:
            lines.append(f"{key}: {_format_scalar(value)}")
    lines.append(FM_DELIM)
    return "\n".join(lines) + "\n"


def extract_title(body: str) -> str | None:
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line:
            # First non-blank line wasn't a heading -- don't guess past it.
            break
    return None


def rewrite(path: Path, fields: dict[str, Any], body: str) -> None:
    path.write_text(serialize(fields) + "\n" + body.lstrip("\n"), encoding="utf-8")
