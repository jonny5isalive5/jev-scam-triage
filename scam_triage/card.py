"""
The evaluation card: what the checker does on public data, stated with what
each number can and can't tell you.

    python -m scam_triage.card                          # validation split
    python -m scam_triage.card --sample 500             # a fixed 500-message sample per group
    python -m scam_triage.card --split test --final     # the one-shot test run (recorded)

Groups:
  scams     IMC 2025 user-reported smishing, English  (label noise: some are genuine messages misreported)
  ordinary  SMS Spam Collection "ham", 2011           (casual chat only; no bank/delivery/code texts)
  old_spam  SMS Spam Collection "spam", 2011          (mostly marketing spam)

For each group: how often the on-device gate forwards a message, the
checker's verdicts, and -- for comparison -- how often the two baselines
(keyword rules and TF-IDF, trained on 2011 SMS at a 1% false-alarm
threshold) flag it. On the scam group it also reports agreement between
Jev's tactic answers and the dataset's GPT-4o tactic labels. Agreement with
GPT-4o is not accuracy.
"""

import argparse
import datetime
import hashlib
import json
import sys

from . import data, engine, jev_client, metrics
from .baselines import KeywordRules, TfidfLogReg
from .evaluate import LEDGER, _git_commit, _ledger_entries

# Dataset tactic labels -> the Jev answer that should match them.
LURE_TO_QUESTION = {"time/urgency": "creates_pressure", "need and greed": "offers_money"}
SCAM_TYPE_TO_ORG = {
    "banking": "bank_or_payments", "government": "government", "delivery": "delivery",
    "telecom": "telecom_or_utility", "hey mum/dad": "none", "wrong number": "none",
}


def _sample(rows, n):
    if not n or n >= len(rows):
        return rows
    ranked = sorted(rows, key=lambda r: hashlib.sha256(data.message_id(r[0]).encode()).hexdigest())
    return ranked[:n]


def groups(split: str, n: int | None) -> dict:
    sms = data.load_split_with_meta("sms_spam", split)
    return {
        "scams": _sample(data.load_split_with_meta("imc25_en", split), n),
        "ordinary": _sample([r for r in sms if r[1] == 0], n),
        "old_spam": _sample([r for r in sms if r[1] == 1], n),
    }


def _kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if not n:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def _baseline_flaggers():
    """
    keyword_rules / tfidf_logreg: fit on 2011 SMS only -- a classifier trained on the data that's
    freely available, applied to today's scams.
    tfidf_in_domain: also trained on the IMC dev split. Expect it to look better than it should: the
    scams (IMC, modern, anonymised) and ordinary messages (2011 chat) differ in era and style, and a
    trained model can learn that difference instead of what makes a scam.
    Every threshold is the 1%-false-alarm point on the ordinary messages of the validation split.
    """
    sms_dev, sms_val = data.load_split("sms_spam", "dev"), data.load_split("sms_spam", "val")
    imc_dev, imc_val = data.load_split("imc25_en", "dev"), data.load_split("imc25_en", "val")
    flaggers = {}
    for name, cls, dev, val in [
        ("keyword_rules", KeywordRules, sms_dev, sms_val),
        ("tfidf_logreg", TfidfLogReg, sms_dev, sms_val),
        ("tfidf_in_domain", TfidfLogReg, sms_dev + imc_dev, sms_val + imc_val),
    ]:
        model = cls().fit(dev)
        val_texts, val_labels = map(list, zip(*val))
        flaggers[name] = (model, metrics.pick_threshold(val_labels, model.score(val_texts)))
    return flaggers


def run(split: str, n: int | None) -> dict:
    flaggers = _baseline_flaggers()
    card = {"split": split, "sample_per_group": n, "mode": jev_client.mode(), "groups": {}}
    for name, rows in groups(split, n).items():
        texts = [t for t, _, _ in rows]
        results = [engine.check(t) for t in texts]
        verdicts = [r.verdict for r in results]
        g = {
            "n": len(rows),
            "gate_forwarded": sum(bool(r.gate) for r in results) / len(rows),
            "likely_scam": verdicts.count(engine.LIKELY_SCAM) / len(rows),
            "be_careful": verdicts.count(engine.BE_CAREFUL) / len(rows),
            "looks_ordinary": verdicts.count(engine.LOOKS_ORDINARY) / len(rows),
            "jev_errors": sum(r.error is not None for r in results),
        }
        for bname, (model, thr) in flaggers.items():
            g[f"{bname}_flagged"] = sum(s >= thr for s in model.score(texts)) / len(rows)
        if name == "scams":
            agreement = {}
            for lure, question in LURE_TO_QUESTION.items():
                ok = [(lure in m["lures"], r.answers[question]["noul"] >= engine.YES)
                      for (_, _, m), r in zip(rows, results) if r.answers]
                agreement[lure] = _kappa([x for x, _ in ok], [y for _, y in ok])
            mapped = [(SCAM_TYPE_TO_ORG[m["scam_type"]], r.answers["claims_to_be"]["choice"])
                      for (_, _, m), r in zip(rows, results) if r.answers and m["scam_type"] in SCAM_TYPE_TO_ORG]
            agreement["scam_type_match"] = sum(a == b for a, b in mapped) / len(mapped) if mapped else None
            g["agreement_with_gpt4o_labels"] = agreement
        card["groups"][name] = g
    return card


def render(card: dict) -> str:
    mock = card["mode"] == "mock"
    out = [f"## Evaluation card -- {card['split']} split, {card['mode'].upper()} mode"
           + (f", {card['sample_per_group']} per group" if card["sample_per_group"] else "")]
    if mock:
        out.append("\n**Mock mode: keyword rules stood in for Jev. These numbers describe those rules, not Jev.**")
    out.append("\n| | scams (IMC 2025) | ordinary (2011) | old spam (2011) |\n|---|---|---|---|")
    g = card["groups"]
    for key, label in [("n", "messages"), ("gate_forwarded", "gate forwards to checker"),
                       ("likely_scam", "verdict: likely scam"), ("be_careful", "verdict: be careful"),
                       ("looks_ordinary", "verdict: looks ordinary"),
                       ("keyword_rules_flagged", "baseline: keyword rules flag"),
                       ("tfidf_logreg_flagged", "baseline: TF-IDF (2011 training) flags"),
                       ("tfidf_in_domain_flagged", "baseline: TF-IDF (incl. IMC training) flags")]:
        cells = [str(g[k][key]) if key == "n" else f"{g[k][key]:.1%}" for k in ("scams", "ordinary", "old_spam")]
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    agr = g["scams"].get("agreement_with_gpt4o_labels", {})
    if agr:
        out.append("\nAgreement with the dataset's GPT-4o tactic labels (Cohen's kappa; not accuracy):")
        for k, v in agr.items():
            out.append(f"- {k}: {'n/a' if v is None else f'{v:.2f}'}")
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", default="val", choices=["val", "test"])
    parser.add_argument("--sample", type=int, default=None, help="fixed sample size per group")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--rerun-reason")
    args = parser.parse_args(argv)
    if args.split == "test":
        if not args.final:
            parser.error("--split test needs --final. The test split is for one final run, not iteration.")
        key = ("card", f"{jev_client.mode()}")
        if any((e["system"], e["dataset"]) == key for e in _ledger_entries()) and not args.rerun_reason:
            parser.error("A test card for this mode is already recorded; pass --rerun-reason to record why.")

    card = run(args.split, args.sample)
    print(render(card))
    out = data.REPO_ROOT / "results" / f"card_{args.split}_{card['mode']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(card, indent=1) + "\n")
    if args.split == "test":
        with LEDGER.open("a") as f:
            f.write(json.dumps({"system": "card", "dataset": card["mode"], "card": card, "commit": _git_commit(),
                                "rerun_reason": args.rerun_reason,
                                "at": datetime.datetime.now(datetime.timezone.utc).isoformat()}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
