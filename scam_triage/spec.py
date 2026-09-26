"""
The single source of truth shared with the Android app.

    python -m scam_triage.spec          # rewrite spec/scam_check_spec.json

The JSON carries everything the phone needs to behave exactly like this
package -- the Jev questions, the domain lists, every regex -- plus golden
cases: messages with the masked text, gate reasons, link facts and verdict
this package produces for them. The Android unit tests load the same file
and must reproduce every golden case, so the two implementations can't
drift apart silently. tests/test_spec.py fails if the committed JSON is
stale.
"""

import dataclasses
import json
import re
from pathlib import Path

from . import engine, gate, jev_client, links, mask, questions

SPEC_PATH = Path(__file__).resolve().parent.parent / "spec" / "scam_check_spec.json"
SPEC_VERSION = 1

GOLDEN_MESSAGES = [
    ("Royal Mail: your parcel is on hold due to an unpaid £1.45 fee. Pay within 24 hrs or it will be returned: "
     "https://rm-redelivery-royalmail.info/pay", None),
    ("running 10 mins late, see you at the cafe", None),
    ("Hi mum, this is my new number, my phone broke. Can you text me back?", False),
    ("Your Uber code is 4829. Never share this code.", None),
    ("URGENT: your HSBC account is locked. Verify your details at http://hsbc-secure-login.xyz within 2 hours", None),
    ("Track your parcel at https://www.royalmail.com/track-your-item.", True),
    ("HMRC: you are owed a tax refund of £326.40. Claim at hmrc-gov-refund.com before it expires", None),
    ("Congratulations! You have WON a £500 voucher. Reply YES to claim", None),
    ("Ηello аll, guуsǃ check this out bit.ly/3xYz", False),
    ("Your Barclays card ending 1234 was used for £49.99 at TESCO. Not you? Call 0345 734 5345", None),
    ("Delivery attempt failed. Reschedule: https://evri-redelivery.top/abc, fee £0.99.", None),
    ("Hey it's Sam, are we still on for Saturday?", True),
    ("Your NHS COVID pass is ready. Download it at nhs-covidpass.info", None),
    ("Netflix: your payment failed. Update your card at www.netflix.com/account", None),
    ("Sorry to bother you, is this Linda? We met at the conference last week", False),
    ("Your O2 bill of £32.50 is ready. View it in the My O2 app.", None),
    ("Email support@secure-paypal-help.com with your password to restore access", None),
    ("Job offer: earn £300/day working from home, WhatsApp +44 7700 900123", None),
    ("Meeting moved to 3pm, room 4012", None),
    ("Your parcel is waiting. Confirm delivery here: https://tinyurl.com/dpd-uk-fee", None),
]


def _fixed_cases():
    """Golden cases: each message with mock answers, plus two with Jev unreachable."""
    cases = []
    for text, sender_known in GOLDEN_MESSAGES:
        answers = jev_client._mock_answers(mask.mask_for_jev(text))
        cases.append((text, sender_known, answers, None))
    cases.append((GOLDEN_MESSAGES[0][0], None, None, "timeout"))
    cases.append((GOLDEN_MESSAGES[1][0], None, None, "timeout"))
    return cases


def _pattern(p: re.Pattern) -> dict:
    """A regex plus whether it ignores case. Java/Kotlin must also use Unicode character classes."""
    return {"pattern": p.pattern, "ignore_case": bool(p.flags & re.IGNORECASE)}


def build() -> dict:
    golden = []
    for text, sender_known, answers, error in _fixed_cases():
        result = engine.decide(text, sender_known, answers, error)
        golden.append({
            "message": text,
            "sender_known": sender_known,
            "answers": answers,
            "error": error,
            "expected": {
                "masked": mask.mask_for_jev(text),
                "gate": gate.gate_reasons(text, sender_known),
                "links": [dataclasses.asdict(l) for l in links.extract_links(text)],
                "verdict": result.verdict,
                "reasons": result.reasons,
                "advice": result.advice,
            },
        })
    return {
        "version": SPEC_VERSION,
        "api": {"base_url": "https://api.typesafe.ai", "path": "/v1/systemone", "model": "jev-latest",
                "request_timeout_s": jev_client.REQUEST_TIMEOUT_S},
        "questions": questions.QUESTIONS,
        "organisation_words": engine._ORG_WORDS,
        "yes_threshold": engine.YES,
        "links": {
            "url_regex": _pattern(links.URL_RE),
            "shorteners": sorted(links.SHORTENERS),
            # Ordered pairs, not an object: the first brand found in a domain wins, and JSON object
            # key order isn't guaranteed by every parser.
            "official_domains": [[k, sorted(v)] for k, v in links.OFFICIAL_DOMAINS.items()],
            "two_part_suffixes": sorted(links._TWO_PART_SUFFIXES),
        },
        "mask": {
            "email_regex": _pattern(mask._EMAIL_RE),
            "phone_regex": _pattern(mask._PHONE_RE),
            "long_number_regex": _pattern(mask._LONG_NUMBER_RE),
        },
        "gate_rules": [[name, _pattern(p)] for name, p in gate.GATE_RULES.items()],  # ordered, like the reasons
        "golden": golden,
    }


def render() -> str:
    return json.dumps(build(), indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPEC_PATH.write_text(render(), encoding="utf-8")
    print(f"Wrote {SPEC_PATH}")
