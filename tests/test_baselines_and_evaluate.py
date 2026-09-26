import pytest

from scam_triage import evaluate
from scam_triage.baselines import KeywordRules, TfidfLogReg


def test_keyword_rules_score_scam_above_ordinary_text():
    rules = KeywordRules()
    scam, normal = rules.score([
        "URGENT: your account is locked. Verify now at http://secure-bank-check.info",
        "running 10 mins late, see you at the cafe",
    ])
    assert scam > normal
    assert "account" in rules.fired_cues("Your account has been suspended")


def test_tfidf_logreg_learns_a_toy_split():
    dev = [("win a free prize now", 1), ("claim your cash reward", 1),
           ("see you at lunch", 0), ("thanks for dinner", 0)] * 3
    model = TfidfLogReg().fit(dev)
    s_scam, s_ok = model.score(["free prize reward", "lunch tomorrow"])
    assert s_scam > s_ok


def test_test_split_requires_final_flag():
    with pytest.raises(SystemExit):
        evaluate.main(["--split", "test"])
