"""Live demo: type a teacher note and watch the rules and Claude clean it."""
import os
import sys

from app.privacy_llm import failures
from app.redact_notes import redact_text


def clean_and_show(text):
    before = len(failures)
    cleaned = redact_text(text)
    print("BEFORE:", text)
    if len(failures) > before:  # Claude's reply was unusable: fail closed
        print("AFTER:  (Claude's reply could not be read, so nothing is shown)")
    else:
        print("AFTER: ", cleaned)
    print()


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set in this terminal tab.")
        print('Set it with: export ANTHROPIC_API_KEY="your-key-here"')
        sys.exit(1)
    if len(sys.argv) > 1:  # one note given on the command line
        clean_and_show(" ".join(sys.argv[1:]))
        return
    print("Type a teacher note and press Enter. Press Enter on an empty line to quit.\n")
    while True:
        text = input("note> ").strip()
        if not text:
            break
        clean_and_show(text)


if __name__ == "__main__":
    main()