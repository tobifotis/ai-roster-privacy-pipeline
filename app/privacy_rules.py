"""Rule-based redaction: catches private details that have a predictable shape."""
import re

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

PHONE = re.compile(
    r"(?<!\d)"                              # not glued to other digits on the left
    r"(?:\+?1[-.\s]?|001[-.\s]?)?"          # optional country code: 1, +1, or 001
    r"(?:\(\d{3}\)\s?|\d{3}[-.\s])"         # area code: (817) or 817- or 817.
    r"\d{3}[-.\s]\d{4}"                     # the rest: 555-1234
    r"(?:\s?(?:x|ext\.?)\s?\d{1,5})?"       # optional extension: x56 or ext. 56
    r"(?!\d)",                              # not glued to other digits on the right
    re.IGNORECASE,
)

MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December"
    r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)"
)

DATE = re.compile(
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"                                   # 3/4/2012
    r"|\b\d{4}-\d{2}-\d{2}\b"                                        # 2012-03-04
    rf"|\b{MONTH}\.? \d{{1,2}}(?:st|nd|rd|th)?(?:, \d{{4}})?\b"      # March 4, 2012
)

# Order matters: emails first, then phones, then dates.
RULES = [("EMAIL", EMAIL), ("PHONE", PHONE), ("DATE", DATE)]


def find_spans(text):
    """Return (start, end, label) for every private detail the rules find."""
    spans = []
    for label, pattern in RULES:
        for m in pattern.finditer(text):
            # skip a match that overlaps one we already found
            if not any(m.start() < e and s < m.end() for s, e, _ in spans):
                spans.append((m.start(), m.end(), label))
    return sorted(spans)


def redact_rules(text):
    # work from the end so earlier positions stay correct as text changes length
    for start, end, label in reversed(find_spans(text)):
        text = text[:start] + f"[{label}]" + text[end:]
    return text


if __name__ == "__main__":
    examples = [
        "Please call Anthony Robinson at 886.737.9402 about the absence.",
        "Parent email is sarah.lopez@example.com, prefers messages after 5pm.",
        "Maria was born 3/4/2012 and enrolled on August 15, 2026.",
        "Call (817) 555-1234 x56 or +1-817-555-9876.",
        "Reminder: library books are due Friday.",
        "Maria's mom Sarah called about the bus.",
    ]
    for example in examples:
        print("BEFORE:", example)
        print("AFTER: ", redact_rules(example))
        print()