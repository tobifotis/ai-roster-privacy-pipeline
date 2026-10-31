"""Tests for the Roster Doctor. None of these call Claude: a fake Claude gives canned replies."""
import csv
import json
import os
from types import SimpleNamespace

import pytest

# the Doctor creates its Claude client when imported; this value is never used to call anything
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

from app import roster_doctor  # noqa: E402
from app.roster_check import check_district  # noqa: E402


def make_district(folder, enrollments):
    """Write a tiny district: two real people plus the enrollment rows we are given."""
    with open(folder / "users.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sourcedId", "role"])
        w.writerow(["u1", "teacher"])
        w.writerow(["u2", "student"])
    with open(folder / "enrollments.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sourcedId", "userSourcedId", "beginDate", "endDate"])
        w.writerows(enrollments)
    return folder


class FakeClaude:
    """Stands in for the Anthropic client and returns whatever text we give it."""

    def __init__(self, *blocks):
        self.blocks = blocks
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        return SimpleNamespace(content=list(self.blocks))


def text(value):
    return SimpleNamespace(type="text", text=value)


def one_problem(tmp_path):
    folder = make_district(tmp_path, [["e1", "u1", "08/15/2026", ""]])
    return check_district(folder)


GOOD_REPLY = json.dumps(
    [{"number": 1, "explanation": "Wrong date format.", "suggested_fix": "Use 2026-08-15."}]
)


# ---- the inspector ----

def test_clean_district_has_no_problems(tmp_path):
    folder = make_district(tmp_path, [["e1", "u1", "2026-08-15", ""], ["e2", "u2", "2026-08-15", "2027-05-30"]])
    assert check_district(folder) == []


@pytest.mark.parametrize("bad", ["08/15/2026", "August 15, 2026", "15-08-2026", "not a date"])
def test_bad_date_formats_are_flagged(tmp_path, bad):
    folder = make_district(tmp_path, [["e1", "u1", bad, ""]])
    problems = check_district(folder)
    assert len(problems) == 1
    assert problems[0].kind == "bad_date"
    assert problems[0].column == "beginDate"
    assert problems[0].value == bad


def test_blank_end_date_is_allowed(tmp_path):
    folder = make_district(tmp_path, [["e1", "u1", "2026-08-15", ""]])
    assert check_district(folder) == []


def test_unknown_person_is_flagged_with_the_right_row(tmp_path):
    # row 1 is the header, so the first enrollment is row 2 and the second is row 3
    folder = make_district(tmp_path, [["e1", "u1", "2026-08-15", ""], ["e2", "nobody", "2026-08-15", ""]])
    problems = check_district(folder)
    assert len(problems) == 1
    assert problems[0].kind == "unknown_reference"
    assert problems[0].row == 3
    assert problems[0].value == "nobody"


def test_inspector_never_changes_the_files(tmp_path):
    folder = make_district(tmp_path, [["e1", "nobody", "08/15/2026", ""]])
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    check_district(folder)
    after = {p.name: p.read_bytes() for p in folder.iterdir()}
    assert before == after


# ---- the explainer (fake Claude) ----

def test_good_reply_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(roster_doctor, "client", FakeClaude(text(GOOD_REPLY)))
    items = roster_doctor.ask_claude(one_problem(tmp_path))
    assert items[0]["suggested_fix"] == "Use 2026-08-15."


def test_reply_wrapped_in_code_fences_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(roster_doctor, "client", FakeClaude(text("```json\n" + GOOD_REPLY + "\n```")))
    assert roster_doctor.ask_claude(one_problem(tmp_path)) is not None


def test_thinking_blocks_are_ignored(tmp_path, monkeypatch):
    thinking = SimpleNamespace(type="thinking", thinking="hmm")
    monkeypatch.setattr(roster_doctor, "client", FakeClaude(thinking, text(GOOD_REPLY)))
    assert roster_doctor.ask_claude(one_problem(tmp_path)) is not None


def test_reply_that_is_not_json_shows_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(roster_doctor, "client", FakeClaude(text("Sorry, I cannot help.")))
    assert roster_doctor.ask_claude(one_problem(tmp_path)) is None


def test_wrong_number_of_answers_shows_nothing(tmp_path, monkeypatch):
    two_answers = json.dumps([
        {"number": 1, "explanation": "a", "suggested_fix": "b"},
        {"number": 2, "explanation": "c", "suggested_fix": "d"},
    ])
    monkeypatch.setattr(roster_doctor, "client", FakeClaude(text(two_answers)))
    assert roster_doctor.ask_claude(one_problem(tmp_path)) is None


def test_answer_missing_a_field_shows_nothing(tmp_path, monkeypatch):
    missing = json.dumps([{"number": 1, "explanation": "only half an answer"}])
    monkeypatch.setattr(roster_doctor, "client", FakeClaude(text(missing)))
    assert roster_doctor.ask_claude(one_problem(tmp_path)) is None


# ---- the human approval step ----

ITEM = {"explanation": "Wrong date format.", "suggested_fix": "Use 2026-08-15."}


@pytest.mark.parametrize("typed, expected", [("y", "approved"), ("Y", "approved"), ("n", "rejected")])
def test_human_answer_decides(tmp_path, monkeypatch, typed, expected):
    monkeypatch.setattr("builtins.input", lambda prompt="": typed)
    assert roster_doctor.ask_human(one_problem(tmp_path)[0], ITEM) == expected


def test_unclear_answer_asks_again(tmp_path, monkeypatch):
    answers = iter(["maybe", "", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    assert roster_doctor.ask_human(one_problem(tmp_path)[0], ITEM) == "rejected"


def test_decision_is_logged_as_one_json_line(tmp_path, monkeypatch):
    log = tmp_path / "logs" / "decisions.jsonl"
    monkeypatch.setattr(roster_doctor, "DECISIONS_LOG", log)
    roster_doctor.record_decision(one_problem(tmp_path / "x" if False else tmp_path)[0], ITEM, "rejected")
    lines = log.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["decision"] == "rejected"
    assert entry["row"] == 2
    assert entry["value"] == "08/15/2026"