# Pre-registration

Written before any live Jev result exists. Anything changed here after live
results have been seen goes in the change log at the bottom, with the reason.

## What is being tested

A scam checker (`scam_triage.engine.check`) that combines exact code checks
(look-alike domains, shortened links, look-alike letters, unknown sender)
with six atomic Jev questions about the masked message, using a rule fixed
in `engine.py`. It returns *likely scam*, *be careful*, or *looks ordinary*,
with reasons.

The question is not "does Jev beat every alternative" -- the public data
can't support a fair answer to that (see Limits). It is: **what does the
checker catch, how often does it warn about ordinary messages, and how does
that compare with classifiers built from the data that is freely
available?**

## Data and splits

Frozen in `splits/` after collapsing near-duplicates:

| Group | Source | Test split |
| --- | --- | --- |
| scams | IMC 2025 smishing reports, English (CC BY 4.0) | 2,969 |
| ordinary | SMS Spam Collection "ham", 2011 | 900 |
| old spam | SMS Spam Collection "spam", 2011 | 119 |

- dev: anything -- reading messages, rewording Jev questions.
- val: checking changes during development.
- test: one live run, recorded in `results/test_ledger.jsonl`.

## The one live test run

```
python -m scam_triage.card --split test --final --sample 500
```

A fixed sample of up to 500 messages per group (chosen by hashing message
ids, not by looking at them), with `TYPESAFE_API_KEY` set. The engine,
questions and combination rule are those at the commit recorded in the
ledger.

## Measures and what would count as success

1. **Catching scams.** "Caught" = *likely scam* or *be careful* on the
   scams group. Compared with the TF-IDF classifier trained on 2011 SMS,
   at its 1%-false-alarm threshold, by paired bootstrap on the same
   messages. *Success:* the checker catches more, with the 95% interval of
   the difference above zero.
2. **Not crying wolf.** On the ordinary group: *likely scam* on at most 2%
   and any warning on at most 10%. *Success:* both met.
3. **Tactics.** Cohen's kappa between Jev's answers and the dataset's GPT-4o
   labels (urgency, greed) and match rate for claimed organisation vs scam
   type. Reported, with no pass mark -- it is agreement with GPT-4o, not
   accuracy.
4. **The gate.** Share of each group forwarded to Jev. Reported.

Whatever the outcome, the README reports all four in the same place, with
failures stated as plainly as successes.

## Expected results, stated in advance

- A TF-IDF model trained on the IMC dev split as well (`tfidf_in_domain`)
  flags about 95% of validation scams at about 1% false alarms. The
  checker is **not expected to beat it**, and the README will not claim
  to. That model is very likely learning the difference between modern
  anonymised reports and 2011 chat, not only what makes a scam -- but
  that can't be shown with this data, so both numbers are reported.
- Mock-mode numbers (keyword rules standing in for Jev) are reported only
  as a floor and are labelled as such.

## Results of the live test run

Run once on 2026-09-26 with `TYPESAFE_API_KEY` set, at commit `d83e220`
(recorded in `results/test_ledger.jsonl`; per-message verdicts in
`results/card_test_live_messages.jsonl`). 500 scams, 500 ordinary, 119 old
spam (the whole old-spam test split). All 1,119 Jev calls succeeded. Before
the run, one made-up message (not from any split) was sent to confirm Jev
was reachable. Nothing listed above was changed after results were seen.

1. **Catching scams: MET.** The checker caught 83.2% of scams vs 54.4% for
   TF-IDF (2011 training): difference +28.8 points, 95% CI +24.0 to +33.8,
   above zero.
2. **Not crying wolf: MET (both parts), with little margin.** *Likely scam*
   on 1.0% of ordinary messages (limit 2%); any warning on 9.0% (limit
   10%). The 9.0% is close to the limit and well above what the baselines
   give (TF-IDF 1.8%, keyword rules 0.4%).
3. **Tactics (reported, no pass mark):** kappa 0.46 for urgency, 0.67 for
   money/greed; claimed organisation matched scam type on 88% of mapped
   messages.
4. **The gate (reported):** forwards 90.0% of scams, 11.4% of ordinary
   messages, 95.0% of old spam.

As expected in advance, the checker did **not** beat TF-IDF trained on IMC
scams as well (96.2% of scams flagged at 0.6% false alarms). It also caught
less old 2011 spam (84.9%) than TF-IDF trained on 2011 SMS (93.3%).

## Limits this data cannot get around

- No modern legitimate messages: bank alerts, delivery updates and
  one-time codes are private and absent from public datasets. The false
  alarm measure covers 2011 casual chat only.
- About 15-22% of IMC "scams" in a hand-checked sample looked like genuine
  messages users misreported, so no system can reach 100% on that group.
- IMC links are anonymised, so the look-alike-domain check -- the
  strongest code check -- never fires on that group.

## Change log

- 2026-09-26: initial version (detection benchmark against SMS Spam
  Collection baselines).
- 2026-09-26: replaced before any Jev code or live run. The project became
  a scam checker with an evaluation card, because public data can't
  support a fair detection benchmark (no modern legitimate messages; IMC
  tactic labels come from GPT-4o). Validation-split numbers in mock mode
  had been seen at this point; no live Jev result had.
- 2026-09-26: before the live test run, with no live Jev result seen (the
  only live call so far was one made-up message, which the network blocked
  before it reached Jev). `card.py` now (a) saves each message's verdict,
  catch and baseline flags next to the card and computes measure 1's paired
  bootstrap in the same run -- the card previously saved only percentages,
  so measure 1 could not have been tested as written above; and (b) in live
  mode, stops at the first failed Jev call without writing the card or the
  ledger, so the one run can't be spent on code-only fallback verdicts. The
  questions, the rule in `engine.py`, the sample and the thresholds are
  unchanged.
- 2026-09-26: the live test run was made (results above). No change to the
  questions, the rule, the sample or the thresholds.
