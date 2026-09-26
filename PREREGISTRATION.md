# Pre-registration

Written before any Jev code exists. Changing anything here after Jev
results have been seen must be recorded in the change log at the bottom,
with the reason.

## Question

Does asking Jev a small set of atomic questions about a message, and
combining the answers in code, flag scam messages better than
(a) a fixed keyword-rule baseline and (b) a TF-IDF + logistic-regression
classifier, at the same false-alarm rate?

## Fixed protocol

- **Data splits** are frozen in `splits/` (60/20/20 dev/val/test,
  stratified, after collapsing near-duplicate messages). They are never
  regenerated.
- **Operating point:** every system flags a message when its score is at
  or above a threshold chosen on the validation split as the lowest
  threshold with false-positive rate <= 1% (`metrics.MAX_FPR`). Missing a
  scam is bad; telling someone their real bank or delivery text is a scam
  is what makes them stop trusting the tool.
- **What each split may be used for:**
  - dev: anything -- reading messages, writing and rewording Jev
    questions, training the TF-IDF baseline.
  - val: choosing thresholds, comparing variants during development.
  - test: one final run per system, recorded in `results/test_ledger.jsonl`.
- **Primary metric:** recall on test at the val-chosen threshold.
  **Secondary:** F1 and false-positive rate on test.
- **A win** means the paired-bootstrap 95% interval for
  (Jev recall - baseline recall) on test is entirely above 0, with test
  FPR no worse than the baseline's. Anything else is reported as a tie or
  a loss, in the README, in the same place a win would have been.

## Jev design constraints

- Atomic questions only, each answerable on its own from the message
  text (for example: does it ask for payment or credentials; does it
  create time pressure or threats; does the claimed sender fit what is
  being asked). No single "is this a scam?" question.
- Answers are combined in code into one score, so the threshold rule
  above applies to Jev exactly as it does to the baselines.
- Exact checks that code can do (for example, extracting links) stay in
  code and are not asked of Jev.

## Hypotheses

- **H1, in-domain (SMS Spam Collection).** Expected result: Jev does
  *not* beat TF-IDF. The dataset is 2011 UK SMS, mostly marketing spam,
  and TF-IDF already reaches 0.93 recall at 1% FPR on val. This run
  validates the pipeline; it is not the headline claim.
- **H2, out-of-domain (to be chosen).** Baselines trained on the SMS
  dev split, evaluated with no retraining on a modern scam/phishing
  set; Jev evaluated zero-shot on the same set. This is the real
  question: whether Jev holds up on scams that don't look like the
  training data. The H2 dataset must be fixed and added to
  `data.DATASETS` before any Jev result on it is seen, and it must
  include hard legitimate messages (real bank, delivery and
  one-time-code texts), not just casual chat.

## Change log

- 2026-09-26: initial version, before any Jev code.
