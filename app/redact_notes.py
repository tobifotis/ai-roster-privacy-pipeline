"""Clean every note once and save the result in notes.text_redacted."""
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Note
from app.privacy_llm import failures, find_spans_llm
from app.privacy_rules import find_spans


def redact_text(text):
    """Rules first, then Claude for what the rules cannot see (names, addresses)."""
    spans = list(find_spans(text))
    for start, end, label in find_spans_llm(text):
        # skip a Claude span that overlaps one the rules already found
        if not any(start < e and s < end for s, e, _ in spans):
            spans.append((start, end, label))
    # replace from the end so earlier positions stay correct
    for start, end, label in sorted(spans, reverse=True):
        text = text[:start] + f"[{label}]" + text[end:]
    return text


def main():
    with SessionLocal() as session:
        notes = session.scalars(select(Note).where(Note.text_redacted.is_(None))).all()
        print(f"Cleaning {len(notes)} notes...")
        saved = skipped = 0
        for note in notes:
            before = len(failures)
            cleaned = redact_text(note.text)
            if len(failures) > before:  # Claude's reply was unusable: fail closed
                skipped += 1
                continue
            note.text_redacted = cleaned
            saved += 1
        session.commit()
    print(f"Saved {saved}, skipped {skipped} (left empty so the API will not serve them).")


if __name__ == "__main__":
    main()