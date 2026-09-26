"""
Exact link checks, done in code on the device. Nothing here needs judgment:
extracting domains, recognising URL shorteners, and spotting a domain that
borrows a well-known brand's name without being that brand's real domain.
"""

import re
from dataclasses import dataclass

URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+|\b(?:[a-z0-9-]+\.)+(?:com|net|org|info|biz|co|uk|us|io|me|ly|xyz|top|link|app|site|online|live|shop|click|gd|at|cc|id|de|es|fr|ru|cn|in)\b(?:/[^\s<>\"']*)?",
    re.IGNORECASE,
)

SHORTENERS = {
    "bit.ly", "bitly.ws", "tinyurl.com", "is.gd", "cutt.ly", "t.ly", "rb.gy", "shorturl.at", "ow.ly",
    "bit.do", "shrtco.de", "t.co", "tiny.cc", "s.id", "rebrand.ly", "buff.ly", "goo.gl", "v.gd", "qr.ae",
}

# Brand name as it appears inside a domain -> the brand's real registrable domains.
# Written from general knowledge; extend it rather than trusting it to be complete.
OFFICIAL_DOMAINS = {
    "royalmail": {"royalmail.com", "royalmail.co.uk"},
    "evri": {"evri.com"},
    "hermes": {"evri.com", "myhermes.co.uk"},
    "dpd": {"dpd.co.uk", "dpd.com"},
    "dhl": {"dhl.com", "dhl.co.uk"},
    "fedex": {"fedex.com"},
    "ups": {"ups.com"},
    "usps": {"usps.com"},
    "amazon": {"amazon.com", "amazon.co.uk"},
    "paypal": {"paypal.com", "paypal.co.uk"},
    "apple": {"apple.com"},
    "icloud": {"icloud.com", "apple.com"},
    "netflix": {"netflix.com"},
    "microsoft": {"microsoft.com", "live.com", "outlook.com"},
    "google": {"google.com", "google.co.uk"},
    "hmrc": {"gov.uk"},
    "dvla": {"gov.uk"},
    "nhs": {"nhs.uk"},
    "irs": {"irs.gov"},
    "barclays": {"barclays.co.uk", "barclays.com"},
    "hsbc": {"hsbc.co.uk", "hsbc.com"},
    "lloyds": {"lloydsbank.com", "lloydsbank.co.uk"},
    "natwest": {"natwest.com"},
    "santander": {"santander.co.uk", "santander.com"},
    "halifax": {"halifax.co.uk"},
    "monzo": {"monzo.com"},
    "revolut": {"revolut.com"},
    "chase": {"chase.com", "chase.co.uk"},
    "wellsfargo": {"wellsfargo.com"},
    "vodafone": {"vodafone.co.uk", "vodafone.com"},
    "o2": {"o2.co.uk"},
    "tmobile": {"t-mobile.com"},
    "verizon": {"verizon.com"},
    "whatsapp": {"whatsapp.com", "wa.me"},
}

# Suffixes where the registrable domain is the last THREE labels (e.g. example.co.uk).
_TWO_PART_SUFFIXES = {"co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "co.in", "co.nz"}


@dataclass(frozen=True)
class LinkFacts:
    domain: str
    registrable: str
    shortener: bool
    lookalike_of: str | None  # brand name borrowed by a domain that isn't the brand's


def registrable_domain(domain: str) -> str:
    labels = domain.lower().strip(".").split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in _TWO_PART_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _domain_of(url: str) -> str:
    url = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    return url.split("/")[0].split("?")[0].split(":")[0].lower().rstrip(".,;)")


def _lookalike_brand(domain: str, registrable: str) -> str | None:
    squashed = re.sub(r"[^a-z0-9]", "", domain)
    for brand, official in OFFICIAL_DOMAINS.items():
        if brand in squashed and registrable not in official:
            return brand
    if re.search(r"(^|[.-])gov([.-]|$)", domain) and not (domain.endswith(".gov.uk") or domain.endswith(".gov")):
        return "government"
    return None


def extract_links(text: str) -> list[LinkFacts]:
    facts = []
    for match in URL_RE.finditer(text):
        domain = _domain_of(match.group(0))
        if "." not in domain:
            continue
        reg = registrable_domain(domain)
        facts.append(LinkFacts(domain, reg, domain in SHORTENERS or reg in SHORTENERS, _lookalike_brand(domain, reg)))
    return facts
