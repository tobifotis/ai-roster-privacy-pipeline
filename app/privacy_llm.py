"""Ask Claude Haiku to find private details in a note."""
import json

import anthropic

MODEL = "claude-haiku-5-5"

PROMPT = """You find private information in teacher notes about students.
List every piece of text that identifies a person or how to reach them:
names of students, parents or teachers, phone numbers, email addresses,
home addresses, and birthdates. Do NOT list school subjects, days of the
week, or ordinary words.
Copy each item exactly as written in the note.
Reply with only a JSON list of strings, like ["Maria Lopez", "817-555-1234"].
If there is nothing private, reply with [].

Note:
"""

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
failures = []  # replies that were not a valid list


def ask_claude(text):
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": PROMPT + text}],
    )
    # keep only the answer blocks and skip any "thinking" blocks
    reply = "".join(b.text for b in response.content if b.type == "text").strip()
    # if Claude wraps the list in a code fence, remove the fence
    if reply.startswith("```"):
        reply = reply.strip("`").removeprefix("json").strip()
    try:
        items = json.loads(reply)
    except json.JSONDecodeError:
        failures.append(reply)
        return []
    return [i for i in items if isinstance(i, str) and i]

def find_spans_llm(text):
    """Turn Claude's list of strings into (start, end, label) positions."""
    spans = []
    for item in set(ask_claude(text)):
        start = text.find(item)
        while start != -1:  # hide every occurrence, not just the first
            spans.append((start, start + len(item), "PII"))
            start = text.find(item, start + 1)
    return sorted(spans)


if __name__ == "__main__":
    examples = [
        "Please call Anthony Robinson at 886.737.9402 about the absence.",
        "Maria's mom Sarah called about the bus.",
        "Reminder: library books are due Friday.",
    ]
    for example in examples:
        print(example)
        print("  Claude found:", ask_claude(example))