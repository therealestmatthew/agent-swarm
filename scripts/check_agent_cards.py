"""Keep the agent roster, the type taxonomy, and the per-agent cards from drifting apart.

Three files describe the same 25 agents:

    plan/agentic-sdlc-design-v0.5.md  §2   -- the roster: who exists, and their role
    plan/agent_taxonomy.md            §2   -- the type assigned to each
    plan/agents/*.md                       -- one card per agent, the detail

Nothing kept them agreeing. The taxonomy's own summary line read "23 existing + 1 proposed = 24
total" while its type counts summed to 25 and its table had 25 rows, and that survived until
someone wrote the cards out one by one. This script is the answer to that class of drift: it is
cheaper to fail a commit than to discover three months later that an agent has a card, a type, and
no dispatcher.

    python3 scripts/check_agent_cards.py           # report; exit 1 on any mismatch
    python3 scripts/check_agent_cards.py --check    # identical -- this script never writes

It is a checker, not a fixer. There is no deterministic repair for "this card describes an agent
nobody dispatches": either the roster is missing a row or the card is dead, and only a human knows
which. It still prints the `CHANGED:` line the pre-commit hook parses, always empty.

Deliberately not enforced: that every Maker names a Checker. The Task Decomposer genuinely has no
independent Checker today, and its card says so as a finding. A check that forced every card to
claim a pairing would convert a recorded design gap into a lie.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter as fm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BLUEPRINT = ROOT / "plan" / "agentic-sdlc-design-v0.5.md"
TAXONOMY = ROOT / "plan" / "agent_taxonomy.md"
CARDS_DIR = ROOT / "plan" / "agents"

TYPES = ("Orchestrator", "Maker", "Checker", "Provider", "Archivist", "Executor")

# Cards that intentionally have no roster row. Both are proposed in agent_taxonomy.md §3 and
# carry status: draft; they enter the roster when the blueprint adopts them.
PROPOSED = {"Vault Scribe", "Vault Checker"}

# Files under plan/agents/ that are not agent cards.
NOT_A_CARD = {"README.md", "card_schema.md"}

REQUIRED_SECTIONS = ("Type", "Pairing", "Purpose", "Inputs", "Outputs", "Write scope", "Layer")


def _table_first_column(text: str, start: str, end: str) -> list[str]:
    """First cell of every data row in the first Markdown table between two headings."""
    section = text.split(start, 1)[1].split(end, 1)[0]
    names = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cell = line.strip("|").split("|")[0].strip().strip("*").strip()
        if cell and cell.lower() != "agent":
            names.append(cell)
    return names


def roster_agents() -> list[str]:
    return _table_first_column(BLUEPRINT.read_text(encoding="utf-8"), "## 2. Agent Roster", "## 3.")


def taxonomy_types() -> dict[str, str]:
    text = TAXONOMY.read_text(encoding="utf-8")
    section = text.split("## §2", 1)[1].split("## §3", 1)[0]
    out: dict[str, str] = {}
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip().strip("*").strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0] and cells[0].lower() != "agent" and cells[1] in TYPES:
            out[cells[0]] = cells[1]
    return out


def card_files() -> list[Path]:
    return sorted(p for p in CARDS_DIR.glob("*.md") if p.name not in NOT_A_CARD)


def card_type(text: str) -> str | None:
    m = re.search(r"^## Type\s*\n+(.+?)$", text, re.MULTILINE)
    if not m:
        return None
    for t in TYPES:
        if re.match(rf"^{t}\b", m.group(1).strip()):
            return t
    return None


def main() -> int:
    errors: list[str] = []

    roster = roster_agents()
    types = taxonomy_types()
    cards = {}
    for path in card_files():
        text = path.read_text(encoding="utf-8")
        fields, _, _ = fm.parse(text)
        cards[fields.get("title", path.stem)] = (path, text, fields)

    if not roster:
        errors.append("could not parse the roster from the blueprint -- has §2's heading changed?")
    if not types:
        errors.append("could not parse types from agent_taxonomy.md §2 -- has its table changed?")

    rel = lambda p: p.relative_to(ROOT)  # noqa: E731

    # 1. every roster row has a card
    for agent in roster:
        if agent not in cards:
            errors.append(f"roster agent '{agent}' has no card in plan/agents/")

    # 2. every card maps to a roster row (or is a declared proposal)
    for name, (path, _, fields) in cards.items():
        if name in roster or name in PROPOSED:
            continue
        errors.append(f"{rel(path)}: card for '{name}', which is in no roster row and not a "
                      f"declared proposal -- either add the roster row or delete the card")

    # 2b. a proposal must say so in its status
    for name in PROPOSED & cards.keys():
        path, _, fields = cards[name]
        if fields.get("status") != "draft":
            errors.append(f"{rel(path)}: '{name}' is proposed but not in the roster, so its "
                          f"status must be 'draft', not '{fields.get('status')}'")

    # 3. declared type matches the taxonomy
    for name, (path, text, _) in cards.items():
        declared = card_type(text)
        if declared is None:
            errors.append(f"{rel(path)}: no '## Type' section naming one of {', '.join(TYPES)}")
            continue
        expected = types.get(name)
        if expected is None:
            errors.append(f"{rel(path)}: '{name}' has no row in agent_taxonomy.md §2")
        elif expected != declared:
            errors.append(f"{rel(path)}: type '{declared}' but agent_taxonomy.md §2 says "
                          f"'{expected}'")

    # 4. layer is declared and known
    for name, (path, _, fields) in cards.items():
        layer = fields.get("layer")
        if not layer:
            errors.append(f"{rel(path)}: no 'layer' in front matter")
        elif layer not in fm.LAYERS:
            errors.append(f"{rel(path)}: layer '{layer}' is not in frontmatter.LAYERS")

    # 5. required sections present.
    # Anchored to a whole line, not a substring: "## Write scope" is a substring of
    # "## Write scopes", so a naive `in text` check passes a heading that has been renamed --
    # which is exactly the drift this rule is for. Caught by negative-testing this script.
    for name, (path, text, _) in cards.items():
        missing = [s for s in REQUIRED_SECTIONS
                   if not re.search(rf"^## {re.escape(s)}\s*$", text, re.MULTILINE)]
        if missing:
            errors.append(f"{rel(path)}: missing required section(s): {', '.join(missing)}")

    if errors:
        print("Agent card check FAILED:")
        for e in errors:
            print(f"  ✗ {e}")
        print("CHANGED:")
        return 1

    print(f"Agent cards: {len(cards)} card(s), {len(roster)} roster row(s), all consistent.")
    print("CHANGED:")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
