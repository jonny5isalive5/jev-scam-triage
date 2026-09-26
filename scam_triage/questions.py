"""
The questions Jev is asked about a message that got past the gate.

Each one is atomic -- answerable on its own from the message, a judgment a
careful person could make in a few seconds -- and none of them is "is this
a scam?". Code combines the answers (see engine.py). Anything code can
determine exactly (links, shorteners, look-alike domains, mixed alphabets,
whether the sender is in the contacts) is decided in code and handed to
Jev as a fact in the state, never asked as a question.
"""

ORGANISATION_TYPES = {
    "bank_or_payments": "A bank, card issuer, payment app, or lender",
    "government": "A government body, tax office, court, police, or health service",
    "delivery": "A courier, postal service, or delivery company",
    "telecom_or_utility": "A mobile network, broadband, energy, or water provider",
    "online_service_or_retailer": "An online shop, streaming service, tech company, or app",
    "employer_or_recruiter": "An employer, recruiter, or job offer",
    "none": "It doesn't claim to come from any organisation (a person, or no identity at all)",
}

QUESTIONS = {
    "asks_for_action": {
        "type": "noul",
        "instructions": "The message asks the reader to tap a link, call or text a number, reply, or make a payment.",
    },
    "asks_for_sensitive_info": {
        "type": "noul",
        "instructions": (
            "The message asks the reader to give or confirm sensitive information: a password, one-time code, "
            "PIN, card or bank details, or personal identity details."
        ),
    },
    "creates_pressure": {
        "type": "noul",
        "instructions": (
            "The message pushes the reader to act quickly: a deadline, a threat of a fee, block, fine, "
            "missed delivery, or other loss if they don't act."
        ),
    },
    "offers_money": {
        "type": "noul",
        "instructions": "The message offers the reader money, a prize, a refund, a reward, or a job with unusually easy pay.",
    },
    "personal_pretext": {
        "type": "noul",
        "instructions": (
            "The message opens a personal conversation from someone the reader may not know: a relative on a "
            "new number, a 'wrong number', a stranger being friendly, or someone asking for a favour."
        ),
    },
    "claims_to_be": {
        "type": "choice",
        "instructions": "What kind of organisation, if any, does the message present itself as coming from?",
        "criteria": ORGANISATION_TYPES,
    },
}

NOUL_QUESTIONS = [name for name, q in QUESTIONS.items() if q["type"] == "noul"]
