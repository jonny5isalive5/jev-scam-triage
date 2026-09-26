"""
The on-device gate: cheap code rules run on every incoming message to decide
whether it is worth asking Jev about at all. Most ordinary messages stop
here and never leave the device.

The gate is deliberately broad -- its job is not to miss scams, not to be
precise. Measured before any Jev code existed: it forwards 87.9% of the
14,879 de-duplicated English scams in the IMC 2025 dataset and 12.1% of the
2011 SMS Spam Collection's ordinary messages. What it missed was mostly
opening-move bait with no link ("You have a parcel pending for delivery."),
which is why an unknown sender is forwarded regardless of content when the
caller knows the sender.
"""

import re
import unicodedata

GATE_RULES = {
    "link": re.compile(
        r"<URL>|https?://|www\.|\b[a-z0-9-]+\.(com|net|org|info|co|uk|ly|me|io|xyz|top|biz|link|app)\b", re.I
    ),
    "contact_point": re.compile(
        r"<PHONE_NUMBER>|<EMAIL_ADDRESS>|\+?\d[\d \-]{7,}\d|\b[\w.]+@[\w.]+\b|whats ?app", re.I
    ),
    "asks_for_action": re.compile(
        r"\b(click|tap|call|reply|text|txt|pay|verify|update|confirm|login|log in|visit|download|contact|"
        r"send|claim|reschedule)\b", re.I
    ),
    "money_or_account": re.compile(
        r"[£$€₹]|\b(rs\.?|inr|usd|refund|payment|prize|cash|fee|bank|account|card)\b", re.I
    ),
}


def mixed_script_words(text: str) -> list[str]:
    """Words mixing Latin letters with Greek or Cyrillic look-alikes ("Ηello аll")."""
    found = []
    for word in re.findall(r"\w+", text):
        scripts = set()
        for ch in word:
            if ch.isalpha():
                name = unicodedata.name(ch, "")
                scripts.add(name.split(" ")[0])
        if "LATIN" in scripts and scripts & {"GREEK", "CYRILLIC"}:
            found.append(word)
    return found


def gate_reasons(text: str, sender_known: bool | None = None) -> list[str]:
    reasons = [name for name, pattern in GATE_RULES.items() if pattern.search(text)]
    if mixed_script_words(text):
        reasons.append("look_alike_letters")
    if sender_known is False:
        reasons.append("unknown_sender")
    return reasons
