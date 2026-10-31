"""The inspector: reads roster CSVs BEFORE loading and lists every problem it finds.

Plain code, no AI. Each problem says which file, which row, and what is wrong.
"""
import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class Problem:
    file: str      # which CSV file
    row: int       # row number as you would see it in a spreadsheet (row 1 is the header)
    column: str    # which column
    value: str     # what was found there
    kind: str      # short label: "bad_date" or "unknown_reference"
    detail: str    # one plain sentence describing the problem


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def check_district(folder):
    """Check one district folder and return a list of Problem objects."""
    folder = Path(folder)
    problems = []

    # Every student and teacher ID that exists, so we can check references to them.
    user_ids = {r["sourcedId"] for r in read_rows(folder / "users.csv")}

    # Row 1 of a spreadsheet is the header, so the first data row is row 2.
    for row_number, r in enumerate(read_rows(folder / "enrollments.csv"), start=2):
        for column in ("beginDate", "endDate"):
            value = r[column]
            if value:  # blank is allowed, a wrong format is not
                try:
                    date.fromisoformat(value)
                except ValueError:
                    problems.append(Problem(
                        "enrollments.csv", row_number, column, value, "bad_date",
                        f"{column} must look like 2026-08-15 (year-month-day).",
                    ))

        if r["userSourcedId"] not in user_ids:
            problems.append(Problem(
                "enrollments.csv", row_number, "userSourcedId", r["userSourcedId"],
                "unknown_reference",
                "This enrollment points to a person who is not in users.csv.",
            ))

    return problems


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "samples/broken_district"
    found = check_district(target)
    print(f"{target}: {len(found)} problem(s)")
    for p in found:
        print(f"  {p.file} row {p.row}, {p.column} = {p.value!r}: {p.detail}")