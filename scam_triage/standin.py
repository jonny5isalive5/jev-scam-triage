"""
Post-hoc comparison, not part of the pre-registration: Jev versus the keyword stand-in (mock
mode) on exactly the messages of the one live test run.

    python -m scam_triage.standin

The live run's per-message verdicts are in results/card_test_live_messages.jsonl. This re-runs
the same test sample offline in mock mode -- the six Jev questions answered by keyword rules
instead -- and compares the two message by message. It never calls Jev and writes nothing to the
test ledger. Written after the live results were seen, so treat it as an honest extra look, not
a pre-registered test.
"""

import json
import random

from . import card, data, jev_client, metrics

LIVE_MESSAGES = data.REPO_ROOT / "results" / "card_test_live_messages.jsonl"
OUT = data.REPO_ROOT / "results" / "standin_comparison.json"


def _diff_interval(a: list[bool], b: list[bool], n_boot: int = 2000, seed: int = 0) -> tuple[float, float, float]:
    """Paired bootstrap for mean(a) - mean(b), resampling messages."""
    rng = random.Random(seed)
    n = len(a)
    diffs = sorted(
        sum(a[i] - b[i] for i in (rng.randrange(n) for _ in range(n))) / n for _ in range(n_boot)
    )
    return (sum(a) - sum(b)) / n, diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot) - 1]


def compare() -> dict:
    if jev_client.mode() != "mock":
        raise SystemExit("Unset TYPESAFE_API_KEY: this comparison must run the keyword stand-in, not Jev.")
    live = {(m["group"], m["id"]): m for m in map(json.loads, LIVE_MESSAGES.read_text().splitlines())}
    ledger_sample = json.loads(open(data.REPO_ROOT / "results" / "card_test_live.json").read())["sample_per_group"]
    _, per = card.run("test", ledger_sample, stop_on_jev_error=False)
    mock = {(m["group"], m["id"]): m for m in per}
    if set(live) != set(mock):
        raise SystemExit("The regenerated sample doesn't match the live run's messages.")

    out = {}
    for group in ("scams", "ordinary", "old_spam"):
        keys = sorted(k for k in live if k[0] == group)
        jev = [live[k]["caught"] for k in keys]
        kw = [mock[k]["caught"] for k in keys]
        diff, lo, hi = _diff_interval(jev, kw)
        out[group] = {
            "n": len(keys),
            "jev_warned": sum(jev) / len(keys),
            "standin_warned": sum(kw) / len(keys),
            "jev_likely_scam": sum(live[k]["verdict"] == "likely_scam" for k in keys) / len(keys),
            "standin_likely_scam": sum(mock[k]["verdict"] == "likely_scam" for k in keys) / len(keys),
            "warned_diff_jev_minus_standin": diff,
            "ci_low": lo,
            "ci_high": hi,
        }
    return out


def main() -> int:
    result = compare()
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    for group, r in result.items():
        print(f"{group:9} n={r['n']:<4} warned: Jev {r['jev_warned']:.1%}  stand-in {r['standin_warned']:.1%}  "
              f"diff {r['warned_diff_jev_minus_standin']:+.3f} (95% CI {r['ci_low']:+.3f} to {r['ci_high']:+.3f})")
    print(f"\nWrote {OUT.relative_to(data.REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
