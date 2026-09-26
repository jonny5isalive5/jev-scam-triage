"""
check(message) -> verdict + plain-English reasons.

    every message -> gate (code, on device)
                       |- nothing to judge -> looks ordinary (never leaves the device)
                       '- something to judge -> mask -> Jev's atomic questions
                                                          + code's exact checks
                                                          -> combined in code -> verdict

Jev is sent only the masked message text -- none of the code's findings.
Earlier projects restated code facts to the model and then let its answer
"confirm" them, which double-counted the same evidence. Here the two
sources stay independent until this module combines them.

The combination rule below was fixed before any evaluation was run. Change
it only with an entry in PREREGISTRATION.md's change log.
"""

from dataclasses import dataclass, field

from . import jev_client
from .gate import gate_reasons, mixed_script_words
from .links import extract_links
from .mask import mask_for_jev

LIKELY_SCAM = "likely_scam"
BE_CAREFUL = "be_careful"
LOOKS_ORDINARY = "looks_ordinary"

YES = 0.5  # a Noul at or above this counts as "yes"

_ORG_WORDS = {
    "bank_or_payments": "your bank or a payment company",
    "government": "a government body",
    "delivery": "a delivery company",
    "telecom_or_utility": "your phone or utility provider",
    "online_service_or_retailer": "an online shop or service",
    "employer_or_recruiter": "an employer or recruiter",
}


@dataclass
class Result:
    verdict: str
    reasons: list[str]
    advice: str
    gate: list[str]
    jev_used: bool
    mode: str
    answers: dict = field(default_factory=dict)
    error: str | None = None


def _advice(verdict: str, org: str | None, personal: bool = False) -> str:
    if verdict == LOOKS_ORDINARY:
        return ("Nothing here looks like a scam, but that isn't a guarantee. If it asks for money or details later, "
                "check again.")
    if personal and org is None:
        return ("Don't reply to this number or send money. If it claims to be someone you know, call them on the "
                "number you already have for them.")
    where = f"{_ORG_WORDS[org]}'s own app or website" if org in _ORG_WORDS else "a number or website you already trust"
    return f"Don't tap links or reply. If you think it might be real, check it through {where}, not this message."


def check(message: str, sender_known: bool | None = None, force: bool = True) -> Result:
    """
    `force=True` (pasting a message in) always runs the full check.
    `force=False` (background monitoring) lets the gate skip ordinary messages.
    """
    gate = gate_reasons(message, sender_known)
    if not force and not gate:
        return Result(LOOKS_ORDINARY, ["No links, contact details, requests, or money mentioned."],
                      _advice(LOOKS_ORDINARY, None), gate, False, jev_client.mode())

    links = extract_links(message)
    lookalikes = sorted({l.lookalike_of for l in links if l.lookalike_of})
    shortener = any(l.shortener for l in links)
    odd_letters = mixed_script_words(message)

    code_reasons = []
    for l in links:
        if l.lookalike_of:
            code_reasons.append(f"The link goes to {l.domain}, which uses the name '{l.lookalike_of}' "
                                f"but isn't its real website.")
    if shortener:
        code_reasons.append("The link is shortened, so you can't see where it really goes.")
    if odd_letters:
        code_reasons.append("Some words use look-alike letters from other alphabets, a trick to slip past filters.")
    if sender_known is False:
        code_reasons.append("The sender isn't in your contacts.")

    try:
        answers = jev_client.ask({"message": mask_for_jev(message)})
    except jev_client.JevUnavailable as exc:
        verdict = LIKELY_SCAM if (lookalikes or odd_letters) else BE_CAREFUL
        reasons = code_reasons + ["Couldn't reach the checker, so only the basic checks ran."]
        return Result(verdict, reasons, _advice(verdict, None), gate, False, jev_client.mode(), error=str(exc))

    said = {name: answers[name]["noul"] >= YES for name, a in answers.items() if a["type"] == "noul"}
    claim = answers["claims_to_be"]
    org = claim["choice"] if claim["choice"] != "none" and claim["probabilities"].get(claim["choice"], 0) >= YES else None

    jev_reasons = []
    if org:
        jev_reasons.append(f"It presents itself as coming from {_ORG_WORDS[org]}.")
    if said.get("asks_for_sensitive_info"):
        jev_reasons.append("It asks for passwords, codes, card or bank details, or personal details.")
    if said.get("asks_for_action"):
        jev_reasons.append("It asks you to tap a link, call, reply, or pay.")
    if said.get("creates_pressure"):
        jev_reasons.append("It rushes you with a deadline or a threat of losing something.")
    if said.get("offers_money"):
        jev_reasons.append("It offers money, a prize, a refund, or easy pay.")
    if said.get("personal_pretext"):
        jev_reasons.append("It starts a personal conversation from someone you may not know.")

    action = said.get("asks_for_action", False)
    likely = (
        bool(lookalikes)
        or said.get("asks_for_sensitive_info", False)
        or (action and (said.get("creates_pressure", False) or said.get("offers_money", False)))
        or (bool(odd_letters) and action)
    )
    careful = (
        (action and (org is not None or shortener or sender_known is False))
        or said.get("personal_pretext", False)
        or said.get("offers_money", False)
        or said.get("creates_pressure", False)
        or shortener
    )
    verdict = LIKELY_SCAM if likely else BE_CAREFUL if careful else LOOKS_ORDINARY
    reasons = code_reasons + jev_reasons or ["Nothing in it matches the patterns scams use."]
    advice = _advice(verdict, org, personal=said.get("personal_pretext", False))
    return Result(verdict, reasons, advice, gate, True, jev_client.mode(), answers)
