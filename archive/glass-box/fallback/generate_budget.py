"""Generate the fallback payload dataset: budget vs actuals with planted anomalies.

Deterministic — same seed, same file, every time. That matters: your golden log and your
demo narrative both assume specific findings exist at specific rows.

    python3 fallback/generate_budget.py

Writes, next to this file:
    budget_actuals.csv   338 rows, Program -> Cost Center -> Account -> Period
    account_master.csv   valid account codes (the join that makes findings checkable)

What is planted, and which agent should catch it, is the table in
07-PAYLOAD-B-BUDGET-FALLBACK.md — kept there rather than in a generated file so there is
one copy to keep true.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 20260825
OUT = Path(__file__).parent

PERIODS = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]

# Program -> [(cost_center, name, monthly_budget_base)]
STRUCTURE: dict[str, list[tuple[str, str, int]]] = {
    "Criminal Operations": [
        ("CC-4100", "Courtroom Staffing", 486_000),
        ("CC-4110", "Case Processing", 212_000),
    ],
    "Civil Operations": [
        ("CC-4200", "Civil Filings", 174_000),
        ("CC-4210", "Small Claims", 88_000),
    ],
    "Facilities": [
        ("CC-4300", "Building Maintenance", 265_000),
        ("CC-4310", "Security Services", 340_000),
    ],
    "Technology": [
        ("CC-4400", "Infrastructure", 298_000),
        ("CC-4410", "Application Support", 156_000),
    ],
}

ACCOUNTS = [
    ("5100", "Salaries — Regular"),
    ("5150", "Salaries — Overtime"),
    ("5200", "Benefits"),
    ("5400", "Professional Services"),
    ("5600", "Supplies"),
    ("5700", "Equipment"),
    ("5800", "Facilities & Utilities"),
]

# Rough share of a cost center's budget by account.
MIX = {
    "5100": 0.44,
    "5150": 0.06,
    "5200": 0.18,
    "5400": 0.12,
    "5600": 0.05,
    "5700": 0.07,
    "5800": 0.08,
}


def main() -> None:
    rng = random.Random(SEED)
    rows: list[dict[str, object]] = []

    for program, centers in STRUCTURE.items():
        for cc, cc_name, base in centers:
            for period in PERIODS:
                for acct, acct_name in ACCOUNTS:
                    budget = round(base * MIX[acct])
                    # Ordinary noise: actuals land within a few percent of budget.
                    actual = round(budget * rng.uniform(0.94, 1.06))
                    rows.append(
                        {
                            "program": program,
                            "cost_center": cc,
                            "cost_center_name": cc_name,
                            "account": acct,
                            "account_name": acct_name,
                            "period": period,
                            "budget": budget,
                            "actual": actual,
                        }
                    )

    index = {(r["cost_center"], r["account"], r["period"]): r for r in rows}

    # ---- PLANT 1: runaway overtime, escalating. HIGH. Trend-visible. ----
    for i, period in enumerate(PERIODS):
        row = index[("CC-4100", "5150", period)]
        row["actual"] = round(int(row["budget"]) * (1.0 + 0.42 * i))

    # ---- PLANT 2: unbudgeted spend — zero budget, real actuals. HIGH. ----
    for period in PERIODS[3:]:
        row = index[("CC-4410", "5700", period)]
        row["budget"] = 0
        row["actual"] = rng.randint(24_000, 31_000)

    # ---- PLANT 3: duplicate posting — same amount, same account, twice. MEDIUM. ----
    # dict() already copies the actual across; the duplicate is the point.
    rows.append(dict(index[("CC-4300", "5400", "2026-03")]))

    # ---- PLANT 4: credit misposting — negative actual. MEDIUM. ----
    index[("CC-4200", "5600", "2026-05")]["actual"] = -14_200

    # ---- PLANT 5: orphan account code, fails the join to account_master. HIGH. ----
    rows.append(
        {
            "program": "Technology",
            "cost_center": "CC-4400",
            "cost_center_name": "Infrastructure",
            "account": "5999",
            "account_name": "Misc Adjustments",
            "period": "2026-04",
            "budget": 0,
            "actual": 67_400,
        }
    )

    # ---- PLANT 6: the honeypot. Looks like a Q2 blowout, is actually a timing shift ----
    # Security services prepaid an annual contract in April and underspent May/June to match.
    # Net variance across the half-year is ~zero. An agent that reads one period in isolation
    # will call it overspend and overreach; the evidence for "overspend" does not survive
    # looking at the adjacent periods. This is the finding designed to fail verification.
    index[("CC-4310", "5400", "2026-04")]["actual"] = round(
        int(index[("CC-4310", "5400", "2026-04")]["budget"]) * 2.9
    )
    for period in ("2026-05", "2026-06"):
        row = index[("CC-4310", "5400", period)]
        row["actual"] = round(int(row["budget"]) * 0.06)

    rows.sort(key=lambda r: (r["cost_center"], r["period"], r["account"]))

    with (OUT / "budget_actuals.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with (OUT / "account_master.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["account", "account_name", "category"])
        for acct, name in ACCOUNTS:
            category = "Personnel" if acct.startswith("51") or acct == "5200" else "Non-Personnel"
            writer.writerow([acct, name, category])

    print(f"wrote {len(rows)} rows to {OUT / 'budget_actuals.csv'}")


if __name__ == "__main__":
    main()
