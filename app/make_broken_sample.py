"""Make a deliberately broken copy of district_a, for practicing the Roster Doctor.

The copy goes in samples/, NOT data/, so the normal loader never touches it.
It has exactly two mistakes:
  1. an enrollment with a date in the wrong format
  2. an enrollment that points to a student who does not exist
"""
import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "district_a"
TARGET = ROOT / "samples" / "broken_district"


def main():
    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(SOURCE, TARGET)

    path = TARGET / "enrollments.csv"
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
        columns = rows[0].keys()

    rows[0]["beginDate"] = "08/15/2026"                     # mistake 1: wrong date format
    rows[1]["userSourcedId"] = "district_a-student-9-999"   # mistake 2: no such student

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Made {TARGET}")
    print("Mistake 1: enrollments.csv row 1 has beginDate 08/15/2026")
    print("Mistake 2: enrollments.csv row 2 points to district_a-student-9-999")


if __name__ == "__main__":
    main()