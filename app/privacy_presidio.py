"""Find private details with Presidio, a free open-source tool."""
from presidio_analyzer import AnalyzerEngine

analyzer = AnalyzerEngine()  # loads the spaCy language model once


def find_spans_presidio(text):
    """Return (start, end, label) for everything Presidio thinks is private."""
    results = analyzer.analyze(text=text, language="en")
    return sorted((r.start, r.end, r.entity_type) for r in results)


if __name__ == "__main__":
    examples = [
        "Please call Anthony Robinson at 886.737.9402 about the absence.",
        "Maria's mom Sarah called about the bus.",
        "Reminder: library books are due Friday.",
    ]
    for example in examples:
        print(example)
        for start, end, label in find_spans_presidio(example):
            print(f"  {label}: {example[start:end]!r}")