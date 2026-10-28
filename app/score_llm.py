"""Score the rules and Claude on the same sample of notes."""
import sys

from app import privacy_llm
from app.privacy_rules import find_spans
from app.score import load_notes, report, score
from app.privacy_presidio import find_spans_presidio


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    notes = load_notes()
    step = max(1, len(notes) // limit)
    sample = notes[::step][:limit]  # evenly spread across both districts
    print(f"Scoring {len(sample)} of {len(notes)} notes\n")

    report("Rules only", score(find_spans, sample))
    report("Presidio (free)", score(find_spans_presidio, sample))
    report("Claude Haiku", score(privacy_llm.find_spans_llm, sample))
    print(f"Claude replies that were not a valid list: {len(privacy_llm.failures)}")


if __name__ == "__main__":
    main()