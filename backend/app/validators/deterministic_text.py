import re

NUMBER_WORDS = {"zero": 0, "no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
SENTENCE = re.compile(r"[^.!?\n]+[.!?]*")


def parse_max_count(rule_text: str, default: int = 1) -> int:
    """Reads a limit such as 'no more than one' from the rule's own wording."""
    match = re.search(
        r"(?:no more than|at most|maximum of|not more than|up to|only)\s+(\w+)",
        rule_text.lower(),
    )
    if match:
        token = match.group(1)
        if token.isdigit():
            return int(token)
        if token in NUMBER_WORDS:
            return NUMBER_WORDS[token]
    return default


def _limit_exclamations(sentence: str, keep: int) -> str:
    """Keeps the first `keep` exclamation marks, turns the rest into full stops."""
    out: list[str] = []
    kept = 0
    for ch in sentence:
        if ch != "!":
            out.append(ch)
        elif kept < keep:
            out.append(ch)
            kept += 1
        elif not out or out[-1] not in ".!?":
            out.append(".")
        # otherwise the extra mark sits next to punctuation and is dropped
    return "".join(out)


def check_exclamations(text: str, max_count: int) -> list[dict]:
    total = text.count("!")
    if total <= max_count:
        return []

    findings: list[dict] = []
    used = 0
    for m in SENTENCE.finditer(text):
        sentence = m.group(0)
        n = sentence.count("!")
        if n == 0:
            continue
        allowed_here = max(0, max_count - used)
        used += n
        if n <= allowed_here:
            continue

        segment = sentence.strip()
        start = m.start() + (len(sentence) - len(sentence.lstrip()))
        findings.append(
            {
                "segment": segment,
                "severity": "low",
                "explanation": (
                    f"The content uses {total} exclamation marks in total; "
                    f"the guideline allows at most {max_count}."
                ),
                "suggested_correction": _limit_exclamations(segment, allowed_here),
                "location": {"start": start, "end": start + len(segment)},
            }
        )
    return findings


def check_all_caps(text: str) -> list[dict]:
    findings: list[dict] = []
    for m in SENTENCE.finditer(text):
        sentence = m.group(0)
        segment = sentence.strip()
        letters = [c for c in segment if c.isalpha()]
        words = re.findall(r"[A-Za-z']+", segment)
        if len(words) >= 3 and len(letters) >= 8 and all(c.isupper() for c in letters):
            start = m.start() + (len(sentence) - len(sentence.lstrip()))
            findings.append(
                {
                    "segment": segment,
                    "severity": "low",
                    "explanation": "This whole sentence is written in capital letters.",
                    "suggested_correction": None,  # the Correction Engine rewrites it in context
                    "location": {"start": start, "end": start + len(segment)},
                }
            )
    return findings