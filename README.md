# Scam Check

Paste in a text message or email and get a verdict -- **likely scam**, **be
careful**, or **looks ordinary** -- with the reasons in plain English. Built
on TypeSafe's [Jev](https://docs.typesafe.ai).

```
LIKELY SCAM

Why:
  - The link goes to rm-redelivery-royalmail.info, which uses the name 'royalmail' but isn't its real website.
  - It presents itself as coming from a delivery company.
  - It asks you to tap a link, call, reply, or pay.
  - It rushes you with a deadline or a threat of losing something.

What to do: Don't tap links or reply. If you think it might be real, check it through
a delivery company's own app or website, not this message.
```

**Status:** working end to end. The single pre-registered live evaluation
run ([PREREGISTRATION.md](PREREGISTRATION.md)) was made on 2026-09-26; its
results are in the Evaluation card below. In short: the checker catches far more modern scams
than a classifier trained on older texts, but on those scams Jev does only a little better than
simple keyword rules answering the same questions -- see "How much does Jev add?".

**Android app: [download the latest version](https://github.com/jonny5isalive5/jev-scam-triage/releases/latest)**
(open it on your phone, install, paste your TypeSafe key, tap Save key).

## Use it

```bash
pip install -e ".[live]"            # or ".[dev]" for offline development
export TYPESAFE_API_KEY=...         # without it, mock mode

python -m scam_triage.cli "paste the message here"
python -m scam_triage.web           # a paste-in page at http://127.0.0.1:8765, on your computer only
```

## How it works

```
message -> gate (code, on your device)
             |- nothing to judge -> looks ordinary (never sent anywhere)
             '- something to judge -> mask -> 6 Jev questions  --.
                                   -> exact code checks  ---------+-> combined in code -> verdict + reasons
```

- **The gate** decides whether a message is worth checking: links, contact
  details, requests to act, money or account words, look-alike letters, or
  an unknown sender. On public data it forwards 88% of real scams and 12%
  of ordinary messages. A pasted message is always checked in full; the
  gate matters for background monitoring (see Roadmap).
- **Code checks** are exact: link domains that borrow a brand's name
  without being its real site, shortened links, words mixing letters from
  different alphabets.
- **Jev answers six atomic questions** -- does it ask you to act; does it
  ask for codes, passwords or card details; does it rush or threaten you;
  does it offer money; does it open a personal conversation from a
  stranger; what organisation does it claim to be. There is no single
  "is this a scam?" question.
- **Code combines the answers** with a fixed rule (`engine.py`). Jev is sent
  only the masked message, never the code's findings, so the two sources of
  evidence stay independent.

## Privacy

What you paste is sent to TypeSafe's API for the Jev questions. Before it
leaves your computer, links, email addresses, phone numbers and any number
of four or more digits (one-time codes, account numbers) are replaced with
placeholders. Money amounts are kept. The link checks run locally. The
paste page listens only on your own computer and doesn't log messages.

## Evaluation card

From public data only, with what each number can and can't show. These are
the **live test-split results** from the one recorded run (2026-09-26, code at
commit `d83e220`; `results/test_ledger.jsonl`). A fixed sample of 500 messages
per group, or the whole group where smaller: the test split has only 119 old
spam messages. All 1,119 messages were answered by Jev; there were no failed calls.

| 500 per group, test, LIVE | scams (IMC 2025) | ordinary (2011) | old spam (2011) |
|---|---|---|---|
| messages | 500 | 500 | 119 |
| gate forwards to checker | 90.0% | 11.4% | 95.0% |
| verdict: likely scam | 55.6% | 1.0% | 49.6% |
| verdict: be careful | 27.6% | 8.0% | 35.3% |
| verdict: looks ordinary | 16.8% | 91.0% | 15.1% |
| keyword rules flag | 21.4% | 0.4% | 79.0% |
| TF-IDF trained on 2011 SMS flags | 54.4% | 1.8% | 93.3% |
| TF-IDF also trained on IMC scams flags | 96.2% | 0.6% | 78.2% |

Against the pre-registered measures:
1. **Catching scams -- met.** The checker caught 83.2% of scams (likely scam
   or be careful) vs 54.4% for TF-IDF trained on 2011 SMS: +28.8 points,
   95% CI +24.0 to +33.8 (paired bootstrap on the same messages).
2. **Not crying wolf -- met, only just.** On ordinary messages: *likely scam*
   on 1.0% (limit 2%) and any warning on 9.0% (limit 10%). That is still
   a lot more warnings than the baselines give on the same messages
   (TF-IDF: 1.8%, keyword rules: 0.4%).
3. **Tactics (agreement with GPT-4o labels, not accuracy):** urgency
   kappa 0.46, money/greed kappa 0.67, claimed organisation matches scam type
   88%.
4. **The gate** forwards 90.0% of scams, 11.4% of ordinary messages and
   95.0% of old spam.

Not beaten: the TF-IDF model also trained on IMC scams flagged 96.2% of
scams at 0.6% false alarms, better than the checker on both counts, as the
pre-registration expected (see the caveat below). On 2011 marketing spam the
checker caught 84.9%, less than the 2011-trained TF-IDF (93.3%), which was
trained on that kind of message.

What these can't tell you:
- **No modern legitimate messages were tested.** Real bank alerts, delivery
  updates and one-time codes aren't in any public dataset, so "ordinary"
  means 2011 casual chat.
- **About 15-22% of the "scams" look genuine** on a hand-checked sample --
  people report real messages too.
- **The look-alike-link check never fires on the scam group**, because
  that dataset anonymised its links.
- **The in-domain TF-IDF number is probably inflated**: modern anonymised
  scam reports and 2011 chat differ in era and style, and a trained model
  can learn that instead of what makes a scam. The pre-registration says in
  advance that the checker isn't expected to beat it here.

Per-message verdicts: `results/card_test_live_messages.jsonl`. The validation
split can be re-run freely with `python -m scam_triage.card --sample 500`
(mock mode without `TYPESAFE_API_KEY`). The test split is for the one recorded run.

## How much does Jev add? (post-hoc)

Added after the live results were seen, so it isn't part of the pre-registration, but it's the
first thing worth asking. The checker has an offline mode where a few keyword rules answer the
six questions instead of Jev. On the **same test messages** as the live run
(`python -m scam_triage.standin`, no Jev calls):

| Same messages | Jev | Keyword stand-in | Jev minus stand-in (95% CI) |
| --- | --- | --- | --- |
| Scams (IMC 2025) warned about | 83.2% | 79.0% | +4.2 points (+0.0 to +8.4) |
| Ordinary texts (2011) warned about | 9.0% | 7.0% | +2.0 points (-1.4 to +5.4) |
| Old spam (2011) warned about | 84.9% | 63.0% | +21.8 points (+12.6 to +31.1) |

- **On modern scams, Jev and the keyword rules are close**: no clear difference in what they
  catch, and Jev warns about ordinary texts slightly more often (within chance). Most of the
  83%-vs-54% win over TF-IDF comes from the checker's structure -- a few atomic questions
  combined by a fixed rule -- not from Jev specifically.
- **On a style the keyword rules weren't written for** (2011 marketing spam), Jev catches clearly
  more. That fits what Jev should be good at -- judging wording it hasn't seen -- but it's one
  small group (119 messages), found after the fact.
- The keyword rules were written by the same person who wrote the questions, after reading some
  IMC messages, so they may suit this dataset better than they would suit new scams.

## Data

| Dataset | Used as | Licence |
| --- | --- | --- |
| [IMC 2025 smishing dataset](https://github.com/reportsmishing/Smishing-Dataset-IMC25) (Agarwal et al., *Fishing for Smishing*, ACM IMC 2025), English, 14,845 after de-duplication | scams | CC BY 4.0 |
| [SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) (Almeida et al., 2011), 5,099 after de-duplication | ordinary messages, old spam | listed by UCI as CC BY 4.0 |

Both are downloaded on first use and checked against pinned SHA-256 hashes.
Messages that differ only in numbers or links are collapsed before
splitting. The IMC dataset's scam-type and tactic labels were produced by
GPT-4o, so agreement with them is reported as agreement, not accuracy.

## Roadmap

1. **This checker** -- paste in, get a verdict.
2. **Gmail labeller** -- checks new mail in the background and adds a
   "Possible scam" label with the reason. Labels, never deletes.
3. **Android** -- first version in `android/` (see below): paste/share checks and warnings for
   incoming texts. Not yet tried on a real phone.

## Background

This replaces [jev-fraud-shield](https://github.com/jonny5isalive5/jev-fraud-shield),
a card-fraud engine that went through five external reviews. The lesson:
card-fraud signals are structured, which rules already handle well, and
without real labelled transactions every synthetic dataset leaked its own
labels. Scam messages are free text that needs judgment, and real labelled
examples exist.

## License

MIT -- see `LICENSE`. Dataset licences are listed above.

## Android app (Moto G15 and other Android phones)

`android/` is a small app that runs the same checker on the phone:

- **Paste or share** a message into Scam Check to get a verdict with reasons.
- **Check incoming texts** (optional switch): each new text goes through the on-phone gate;
  ordinary texts are never sent anywhere, risky ones raise a warning notification. Nothing is
  deleted or blocked. In the background a warning is raised for a *likely scam*, or for *be careful*
  only when Jev actually judged the text -- "couldn't reach Jev" (no key, offline) never pops up a
  warning, or every text from a non-contact would.
- Link checks, masking and the gate run on the phone. With a TypeSafe key saved in the app,
  masked messages are also sent to Jev; without one, only the basic checks run.
- Background mode applies the gate first, so it differs a little from the paste-in numbers in the
  evaluation card. Recomputed after the fact from the same logged test run
  (`results/card_test_live_messages.jsonl`, counting only messages the gate passes): 78.6% of test
  scams raise a warning (vs 83.2% pasted in), and 2.2% of ordinary texts do (vs 9.0%).

The phone and the Python package share one rules file, `spec/scam_check_spec.json` (written by
`python -m scam_triage.spec`). The Android unit tests replay every worked example in it and must
match the Python results exactly, so the app can't drift from the version that was evaluated.

CI also runs the real app on an Android 14 emulator (`android/ci/emulator-smoke.sh`): UI flows,
then real SMS messages sent to the emulator -- a scam text must raise a warning, an ordinary one
must not.

Build: `cd android && ./gradlew assembleDebug` (needs the Android SDK). The APK is installed
directly ("install unknown apps"), not through the Play Store. Pushing a tag such as `v0.1.3`
runs `.github/workflows/release.yml`, which tests, builds and attaches the APK to a GitHub Release.
