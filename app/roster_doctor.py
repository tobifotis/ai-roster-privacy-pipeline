"""The Roster Doctor: the inspector finds problems, Claude explains them in plain English.

Claude only explains. It never decides what is wrong and never changes data.
"""
import json
import os
import sys

import anthropic

from app.roster_check import check_district
from datetime import datetime, timezone
from pathlib import Path

MODEL = "claude-haiku-5-5"
client = anthropic.Anthropic()

PROMPT = """You help a school office fix a roster file that failed to load.
Below is a numbered list of problems found by an automated checker.
For EACH problem, write:
- "explanation": one or two plain sentences a school office worker can understand
- "suggested_fix": one concrete sentence saying what to change

Rules:
- Only describe the problems listed. Do not invent others.
- For a date in the wrong format, you may show the same date in the right format.
- Do not guess a missing person's ID. Say what to check instead.

Reply with ONLY a JSON list, one object per problem, in the same order, with the keys
"number", "explanation", and "suggested_fix". No other text.

Problems:
{problems}
"""


def ask_claude(problems):
    """Return a list of {number, explanation, suggested_fix}, or None if the reply is unusable."""
    lines = [
        f"{i}. {p.file}, row {p.row}, column {p.column}, value {p.value!r}: {p.detail}"
        for i, p in enumerate(problems, start=1)
    ]
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": PROMPT.format(problems="\n".join(lines))}],
    )
    # the reply can include a "thinking" block, so keep only the text blocks
    reply = "".join(b.text for b in response.content if b.type == "text").strip()
    if reply.startswith("```"):
        reply = reply.strip("`").removeprefix("json").strip()
    try:
        items = json.loads(reply)
    except json.JSONDecodeError:
        return None
    # fail closed: one usable answer per problem, or nothing
    if not isinstance(items, list) or len(items) != len(problems):
        return None
    for item in items:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(k), str) for k in ("explanation", "suggested_fix")
        ):
            return None
    return items


DECISIONS_LOG = Path("logs") / "doctor_decisions.jsonl"


def record_decision(problem, item, decision):
    """Append one line to the decisions log. This is the ONLY thing the Doctor writes."""
    DECISIONS_LOG.parent.mkdir(exist_ok=True)
    entry = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file": problem.file,
        "row": problem.row,
        "column": problem.column,
        "value": problem.value,
        "suggested_fix": item["suggested_fix"],
        "decision": decision,
    }
    with open(DECISIONS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def ask_human(problem, item):
    """Show one suggestion and wait for a person to answer y or n."""
    print(f"{problem.file} row {problem.row}, {problem.column} = {problem.value!r}")
    print(f"  What happened: {item['explanation']}")
    print(f"  Suggested fix: {item['suggested_fix']}")
    while True:
        answer = input("  Approve this suggestion? [y/n] ").strip().lower()
        if answer in ("y", "n"):
            print()
            return "approved" if answer == "y" else "rejected"


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set in this terminal tab.")
        sys.exit(1)
    target = sys.argv[1] if len(sys.argv) > 1 else "samples/broken_district"
    problems = check_district(target)
    if not problems:
        print(f"{target}: no problems found. Nothing to explain.")
        return
    print(f"{target}: {len(problems)} problem(s) found by the inspector.\n")
    items = ask_claude(problems)
    if items is None:
        print("Claude's reply could not be read, so no suggestions are shown.")
        return
    for p, item in zip(problems, items):
        decision = ask_human(p, item)
        record_decision(p, item, decision)
    print(f"Decisions saved to {DECISIONS_LOG}. Nothing in your data was changed.")
    print("A person still has to make the approved fixes in the CSV files.")


if __name__ == "__main__":
    main()