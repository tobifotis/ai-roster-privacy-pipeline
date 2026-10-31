import pytest

from app.privacy_rules import find_spans, redact_rules


def test_email_is_hidden():
    text = "Parent email is sarah.lopez@example.com, prefers messages after 5pm."
    assert redact_rules(text) == "Parent email is [EMAIL], prefers messages after 5pm."


@pytest.mark.parametrize("phone", [
    "886.737.9402",
    "886-737-9402",
    "(817) 555-1234",
    "(817) 555-1234 x56",
    "+1-817-555-9876",
    "001-221-248-9513x4332",
])
def test_phone_formats_are_hidden(phone):
    assert redact_rules(f"Call {phone} today.") == "Call [PHONE] today."


@pytest.mark.parametrize("date", [
    "3/4/2012",
    "2012-03-04",
    "March 4, 2012",
    "August 15, 2026",
])
def test_date_formats_are_hidden(date):
    assert redact_rules(f"Born {date}.") == "Born [DATE]."


def test_ordinary_sentences_are_left_alone():
    text = "Reminder: library books are due Friday."
    assert redact_rules(text) == text


def test_long_digit_strings_are_not_phones():
    text = "Order number 12345678901234 shipped."
    assert redact_rules(text) == text


def test_rules_cannot_see_names():
    # a known limit, written down on purpose: names have no fixed shape,
    # which is why Claude is part of the pipeline
    text = "Maria's mom Sarah called about the bus."
    assert redact_rules(text) == text


def test_find_spans_reports_each_match_in_order():
    spans = find_spans("Call 886.737.9402 or write a@b.co")
    assert [label for _, _, label in spans] == ["PHONE", "EMAIL"]