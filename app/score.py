"""Score a privacy detector against the answer key in notes.csv."""
import csv
import json
import re
from pathlib import Path

from app.privacy_rules import find_spans

DATA = Path("data")


def load_notes():
    notes = []
    for folder in sorted(DATA.iterdir()):
        path = folder / "notes.csv"
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    notes.append({
                        "tenant": folder.name,
                        "id": row["noteId"],
                        "text": row["text"],
                        "labels": json.loads(row["pii_labels"]),
                    })
    return notes


def gold_spans(text, labels):
    """Where each private string from the answer key sits in the text."""
    spans = []
    for label in set(labels):  # set() removes duplicate names in the key
        for m in re.finditer(re.escape(label), text):
            spans.append((m.start(), m.end(), label))
    return spans


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def score(detector, notes=None):
    """detector: a function that takes text and returns a list of (start, end, ...)."""
    notes = notes or load_notes()
    caught = missed = correct = wrong = 0
    miss_examples, wrong_examples = [], []
    for n in notes:
        gold = gold_spans(n["text"], n["labels"])
        found = detector(n["text"])
        for g in gold:
            if any(overlaps(g, f) for f in found):
                caught += 1
            else:
                missed += 1
                miss_examples.append((g[2], n["text"]))
        for f in found:
            if any(overlaps(f, g) for g in gold):
                correct += 1
            else:
                wrong += 1
                wrong_examples.append((n["text"][f[0]:f[1]], n["text"]))
    recall = caught / (caught + missed) if caught + missed else 0.0
    precision = correct / (correct + wrong) if correct + wrong else 0.0
    return {
        "recall": recall, "precision": precision,
        "caught": caught, "missed": missed, "correct": correct, "wrong": wrong,
        "miss_examples": miss_examples, "wrong_examples": wrong_examples,
    }


def report(name, result):
    print(f"=== {name} ===")
    print(f"Recall:    {result['recall']:.1%}  ({result['caught']} caught, {result['missed']} missed)")
    print(f"Precision: {result['precision']:.1%}  ({result['correct']} correct, {result['wrong']} wrongly hidden)")
    print("Examples of misses:")
    for label, text in result["miss_examples"][:5]:
        print(f"  missed {label!r} in: {text}")
    print("Examples of wrongly hidden:")
    for hidden, text in result["wrong_examples"][:5]:
        print(f"  hid {hidden!r} in: {text}")
    print()


if __name__ == "__main__":
    report("Rules only", score(lambda text: find_spans(text)))