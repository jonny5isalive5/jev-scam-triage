"""
The two baselines any Jev pipeline has to be compared against.

Both are fixed before any Jev code exists, so the comparison can't be
tuned toward a result. Every system exposes the same interface:
`fit(dev_rows)` then `score(texts) -> list[float]`, where a higher score
means more likely scam. The decision threshold is not chosen here --
evaluate.py picks it on the validation split under one fixed rule for
every system.
"""

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

# Written from general knowledge of scam and spam messages, not by
# reading this dataset's messages. Each pattern is one cue; the score is
# how many distinct cues fire.
KEYWORD_CUES = {
    "link": r"https?://|www\.|\b[a-z0-9-]+\.(com|net|org|co\.uk|info|biz|ly)\b",
    "prize": r"\b(win|won|winner|prize|reward|award|selected|congratulations)\b",
    "free": r"\bfree\b",
    "claim": r"\b(claim|redeem|collect)\b",
    "urgency": r"\b(urgent|immediately|now|expire[sd]?|final notice|last chance|within \d+ (hours?|days?))\b",
    "money": r"[£$€]\s?\d|\b(cash|credit|loan|refund)\b",
    "reply_to_number": r"\b(txt|text|reply|send|call)\b[^.]{0,20}\b\d{4,}\b",
    "long_number": r"\b\d{5,}\b",
    "account": r"\b(account|verify|verification|password|pin|suspended|locked|security)\b",
    "delivery": r"\b(parcel|package|delivery|courier)\b",
    "unsubscribe": r"\b(stop|unsubscribe|opt ?out)\b",
}


class KeywordRules:
    name = "keyword_rules"

    def __init__(self):
        self._patterns = {k: re.compile(p, re.IGNORECASE) for k, p in KEYWORD_CUES.items()}

    def fit(self, dev_rows):
        return self  # nothing to learn; the cue list is fixed

    def fired_cues(self, text: str) -> list[str]:
        return [name for name, pat in self._patterns.items() if pat.search(text)]

    def score(self, texts):
        return [float(len(self.fired_cues(t))) for t in texts]


class TfidfLogReg:
    """A standard text classifier trained on the dev split. The strong baseline."""

    name = "tfidf_logreg"

    def __init__(self):
        self._model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            LogisticRegression(max_iter=2000, class_weight="balanced"),
        )

    def fit(self, dev_rows):
        texts, labels = zip(*dev_rows)
        self._model.fit(list(texts), list(labels))
        return self

    def score(self, texts):
        return list(self._model.predict_proba(list(texts))[:, 1])


BASELINES = {cls.name: cls for cls in (KeywordRules, TfidfLogReg)}
