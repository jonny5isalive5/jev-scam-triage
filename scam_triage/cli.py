"""
Paste-in checker for the terminal.

    python -m scam_triage.cli "Royal Mail: your parcel is on hold..."
    python -m scam_triage.cli            # then paste, and press Ctrl-D (Ctrl-Z Enter on Windows)
"""

import sys

from .engine import BE_CAREFUL, LIKELY_SCAM, check

LABELS = {LIKELY_SCAM: "LIKELY SCAM", BE_CAREFUL: "BE CAREFUL", "looks_ordinary": "LOOKS ORDINARY"}


def render(result) -> str:
    lines = [LABELS[result.verdict], "", "Why:"]
    lines += [f"  - {r}" for r in result.reasons]
    lines += ["", f"What to do: {result.advice}"]
    if result.mode == "mock":
        lines += ["", "(mock mode: no TYPESAFE_API_KEY, so keyword rules stood in for Jev)"]
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    message = " ".join(argv) if argv else sys.stdin.read()
    if not message.strip():
        print("Paste a message to check.", file=sys.stderr)
        return 2
    print(render(check(message)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
