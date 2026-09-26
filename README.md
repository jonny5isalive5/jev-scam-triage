# Jev Scam Triage

Scam and phishing message triage using TypeSafe's [Jev](https://docs.typesafe.ai),
evaluated on real labelled data against fixed baselines.

**Status: evaluation harness and baselines only. No Jev code yet.** The
comparison is set up first, and the success criteria are written down in
[PREREGISTRATION.md](PREREGISTRATION.md) before any Jev result exists.

## Why this exists

This follows [jev-fraud-shield](https://github.com/jonny5isalive5/jev-fraud-shield),
a card-fraud engine that went through five external reviews. Its lesson:
card-fraud signals are structured (device, velocity, amount, geography),
which rules handle well, and without real labelled transactions every
synthetic dataset leaked its own labels. Scam messages are the opposite
case: the input is free text that needs judgment, and real labelled data
exists.

## Data

| Dataset | Messages | Scam/spam | Notes |
| --- | --- | --- | --- |
| `sms_spam` | 5,574 raw, 5,099 after de-duplication | 598 | UCI SMS Spam Collection (Almeida et al., 2011). UCI lists it under CC BY 4.0. 2011 UK SMS; "spam" is mostly marketing, not modern scams. |

The file is downloaded on first use (not committed) and checked against
a pinned SHA-256. Messages that differ only in digits or links are
collapsed before splitting, so a campaign resent with different phone
numbers can't land in both training and test.

A modern scam/phishing dataset with realistic legitimate messages (bank,
delivery, one-time-code texts) is still to be chosen -- see H2 in the
pre-registration.

## Baselines (validation split)

Thresholds are chosen on this same split, so these numbers are
optimistic. Test-split numbers come from one recorded final run.

| System | Recall | Precision | FPR | F1 |
| --- | --- | --- | --- | --- |
| Keyword rules (fixed cue list) | 0.833 | 0.962 | 0.004 | 0.893 |
| TF-IDF + logistic regression | 0.933 | 0.926 | 0.010 | 0.929 |

## Usage

```bash
pip install -e ".[dev]"
python -m scam_triage.evaluate                       # baselines on validation
python -m scam_triage.evaluate --split test --final  # the one-shot test run (recorded)
python -m pytest
```

Test runs are appended to `results/test_ledger.jsonl` with the commit
hash. Running a system on test a second time requires `--rerun-reason`,
which is recorded too.

## License

MIT -- see `LICENSE`. Dataset licences are separate; see the table above.
