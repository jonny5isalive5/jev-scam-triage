"""
Evaluate systems on the validation split, or -- once, deliberately -- on test.

    python -m scam_triage.evaluate                      # all baselines, validation split
    python -m scam_triage.evaluate --split test --final # the one-shot test run

Every system is fit on dev, its threshold is picked on val with the same
rule (metrics.pick_threshold), and only then scored on the requested
split. Test runs are appended to results/test_ledger.jsonl. A second test
run for the same system is refused unless --rerun-reason is given, and
that reason is recorded: the ledger is the audit trail showing the test
set was not used to tune anything.
"""

import argparse
import datetime
import json
import subprocess
import sys

from . import data, metrics
from .baselines import BASELINES

LEDGER = data.REPO_ROOT / "results" / "test_ledger.jsonl"


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=data.REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _ledger_entries() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def run_system(system_cls, dataset: str, split: str) -> dict:
    dev = data.load_split(dataset, "dev")
    val = data.load_split(dataset, "val")
    target = data.load_split(dataset, split)

    system = system_cls().fit(dev)
    val_texts, val_labels = zip(*val)
    threshold = metrics.pick_threshold(list(val_labels), system.score(list(val_texts)))

    texts, labels = zip(*target)
    preds = [s >= threshold for s in system.score(list(texts))]
    return {"system": system_cls.name, "dataset": dataset, "split": split, "threshold": threshold,
            "n": len(labels), "n_positive": sum(labels), **metrics.summarize(list(labels), preds),
            "_labels": list(labels), "_preds": preds}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default="sms_spam", choices=sorted(data.DATASETS))
    parser.add_argument("--split", default="val", choices=["val", "test"])
    parser.add_argument("--systems", nargs="*", default=sorted(BASELINES))
    parser.add_argument("--final", action="store_true", help="required for --split test")
    parser.add_argument("--rerun-reason", help="required to evaluate a system on test a second time")
    args = parser.parse_args(argv)

    if args.split == "test":
        if not args.final:
            parser.error("--split test needs --final. The test split is for one final run, not iteration.")
        already = {(e["system"], e["dataset"]) for e in _ledger_entries()}
        repeats = [s for s in args.systems if (s, args.dataset) in already]
        if repeats and not args.rerun_reason:
            parser.error(f"{repeats} already have a test result in {LEDGER.name}; pass --rerun-reason to record why.")

    results = [run_system(BASELINES[name], args.dataset, args.split) for name in args.systems]

    print(f"{args.dataset} / {args.split}  (operating point: FPR <= {metrics.MAX_FPR:.0%} on val)\n")
    print(f"{'system':<16}{'recall':>8}{'precision':>11}{'fpr':>8}{'f1':>7}{'tp':>6}{'fp':>5}{'fn':>5}")
    for r in results:
        print(f"{r['system']:<16}{r['recall']:>8.3f}{r['precision']:>11.3f}{r['fpr']:>8.3f}"
              f"{r['f1']:>7.3f}{r['tp']:>6}{r['fp']:>5}{r['fn']:>5}")

    if len(results) >= 2:
        a, b = results[-1], results[0]
        for metric in ("recall", "f1"):
            cmp = metrics.paired_bootstrap(a["_labels"], a["_preds"], b["_preds"], metric=metric)
            print(f"\n{a['system']} - {b['system']} {metric}: {cmp['diff']:+.3f} "
                  f"(95% CI {cmp['ci_low']:+.3f} to {cmp['ci_high']:+.3f})")

    if args.split == "test":
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a") as f:
            for r in results:
                entry = {k: v for k, v in r.items() if not k.startswith("_")}
                entry.update(commit=_git_commit(), rerun_reason=args.rerun_reason,
                             at=datetime.datetime.now(datetime.timezone.utc).isoformat())
                f.write(json.dumps(entry) + "\n")
        print(f"\nRecorded in {LEDGER.relative_to(data.REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
