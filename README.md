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

**Status:** working end to end in mock mode (keyword rules standing in for
Jev). The single live evaluation run is pre-registered in
[PREREGISTRATION.md](PREREGISTRATION.md) and hasn't happened yet.

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

From public data only, with what each number can and can't show. Current
numbers are **mock mode on the validation split** -- they describe the
keyword stand-in, not Jev. The live test-split card replaces them after the
one recorded run.

| 500 per group, validation, MOCK | scams (IMC 2025) | ordinary (2011) | old spam (2011) |
|---|---|---|---|
| gate forwards to checker | 88.2% | 11.6% | 93.3% |
| verdict: likely scam | 49.6% | 1.4% | 33.3% |
| verdict: be careful | 30.4% | 6.8% | 20.8% |
| verdict: looks ordinary | 20.0% | 91.8% | 45.8% |
| keyword rules flag | 24.2% | 0.0% | 83.3% |
| TF-IDF trained on 2011 SMS flags | 50.8% | 1.2% | 93.3% |
| TF-IDF also trained on IMC scams flags | 95.2% | 1.4% | 80.0% |

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

Reproduce: `python -m scam_triage.card --sample 500`.

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
3. **Android** -- a personal app that checks incoming texts through the
   gate and shows a warning. Installed directly, not through the Play Store.

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
  deleted or blocked.
- Link checks, masking and the gate run on the phone. With a TypeSafe key saved in the app's
  Settings, masked messages are also sent to Jev; without one, only the basic checks run.

The phone and the Python package share one rules file, `spec/scam_check_spec.json` (written by
`python -m scam_triage.spec`). The Android unit tests replay every worked example in it and must
match the Python results exactly, so the app can't drift from the version that was evaluated.

Build: `cd android && ./gradlew assembleDebug` (needs the Android SDK). The APK is installed
directly ("install unknown apps"), not through the Play Store.
