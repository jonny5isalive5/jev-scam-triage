"""
The one place that talks to Jev.

Live mode (TYPESAFE_API_KEY set and typesafe-sdk installed) uses the real
SDK, whose client already has a per-request timeout and a retry policy that
only retries transient failures (timeouts, 408/429/5xx). Both are set
explicitly here so the whole check has a bounded worst case.

Without a key, a mock answers instead. The mock is a handful of keyword
rules shaped like Jev's answers so the rest of the pipeline can be built
and tested offline. It is not a model; numbers produced in mock mode
measure those keyword rules, not Jev, and are labelled as such everywhere.
"""

import os
import re

from .questions import ORGANISATION_TYPES, QUESTIONS

REQUEST_TIMEOUT_S = 5.0   # per HTTP attempt
TOTAL_RETRY_BUDGET_S = 12.0  # across all retries of one check


class JevUnavailable(RuntimeError):
    """Jev could not be reached or returned something unusable."""


def mode() -> str:
    return "live" if os.environ.get("TYPESAFE_API_KEY", "").strip() else "mock"


_client = None


def _live_client():
    global _client
    if _client is None:
        try:
            from typesafe_sdk import RetryPolicy, TypeSafeClient
        except ImportError as exc:
            raise JevUnavailable('TYPESAFE_API_KEY is set but typesafe-sdk isn\'t installed: pip install -e ".[live]"') from exc
        _client = TypeSafeClient(
            timeout=REQUEST_TIMEOUT_S,
            retry=RetryPolicy(max_retries=2, timeout=TOTAL_RETRY_BUDGET_S),
        )
    return _client


def ask(state: dict) -> dict:
    """Ask every question in questions.QUESTIONS about `state`. Returns plain dicts."""
    if mode() == "mock":
        return _mock_answers(state["message"])
    from typesafe_sdk import TypeSafeError

    try:
        response = _live_client().system_one(state=state, questions=QUESTIONS)
    except TypeSafeError as exc:
        raise JevUnavailable(str(exc)) from exc
    answers = {}
    for name, answer in response.answers.items():
        if answer.type == "noul":
            answers[name] = {"type": "noul", "noul": answer.noul}
        elif answer.type == "choice":
            answers[name] = {"type": "choice", "choice": answer.choice, "confidence": answer.confidence,
                             "probabilities": dict(answer.probabilities)}
    missing = set(QUESTIONS) - set(answers)
    if missing:
        raise JevUnavailable(f"Jev's response had no answer for {sorted(missing)}")
    return answers


# --- mock: keyword rules shaped like Jev's answers (NOT a model) -------------

_MOCK_NOULS = {
    "asks_for_action": r"\b(click|tap|call|text|reply|pay|visit|follow|open|download|log ?in|update|verify|confirm)\b|<URL>",
    "asks_for_sensitive_info": r"\b(password|passcode|pin|one.time|otp|code|card (number|details)|bank details|sort code|security question|date of birth|verify your (identity|account|details))\b",
    "creates_pressure": r"\b(urgent|immediately|today|within \d+|expires?|expired|suspended|blocked|locked|final|last chance|overdue|unpaid|fine|penalt|returned|cancel)\w*",
    "offers_money": r"\b(won|winner|prize|reward|refund|cash|bonus|free|earn|claim|compensation|payout)\b",
    "personal_pretext": r"\b(hi mum|hi mom|hi dad|new number|new phone|wrong number|sorry to bother|is this|remember me|lost my phone)\b",
}
_MOCK_ORGS = {
    "bank_or_payments": r"\b(bank|card|paypal|account|payment|credit|loan|barclays|hsbc|lloyds|natwest|santander|chase|monzo|revolut)\b",
    "government": r"\b(hmrc|gov|tax|dvla|nhs|irs|court|police|council|fine)\b",
    "delivery": r"\b(parcel|package|delivery|courier|royal mail|evri|dpd|dhl|ups|fedex|usps|redeliver)\w*",
    "telecom_or_utility": r"\b(ee|o2|vodafone|three|bill|energy|broadband|network|sim)\b",
    "online_service_or_retailer": r"\b(amazon|netflix|apple|icloud|microsoft|google|order|subscription|account suspended)\b",
    "employer_or_recruiter": r"\b(job|hiring|recruit|salary|work from home|part.time)\b",
}


def _mock_answers(message: str) -> dict:
    answers = {}
    for name, pattern in _MOCK_NOULS.items():
        hit = bool(re.search(pattern, message, re.IGNORECASE))
        answers[name] = {"type": "noul", "noul": 0.9 if hit else 0.1}
    choice = next((org for org, p in _MOCK_ORGS.items() if re.search(p, message, re.IGNORECASE)), "none")
    probs = {org: (0.8 if org == choice else 0.2 / (len(ORGANISATION_TYPES) - 1)) for org in ORGANISATION_TYPES}
    answers["claims_to_be"] = {"type": "choice", "choice": choice, "confidence": 0.8, "probabilities": probs}
    return answers
