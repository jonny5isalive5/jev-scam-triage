import pytest

from scam_triage import card, engine, evaluate


def _result(verdict, error=None):
    return engine.Result(verdict, [], "", ["link"], error is None, "live", error=error)


def test_live_run_stops_at_first_failed_jev_call(monkeypatch):
    calls = []

    def fake_check(text):
        calls.append(text)
        return _result(engine.BE_CAREFUL, error="Connection error: 403 Forbidden") if text == "b" else _result(engine.LIKELY_SCAM)

    monkeypatch.setattr(engine, "check", fake_check)
    with pytest.raises(card.JevCallFailed):
        card._check_all(["a", "b", "c"], stop_on_jev_error=True)
    assert calls == ["a", "b"]


def test_failed_test_run_writes_nothing(monkeypatch, tmp_path):
    ledger = tmp_path / "test_ledger.jsonl"
    monkeypatch.setattr(card, "LEDGER", ledger)
    monkeypatch.setattr(evaluate, "LEDGER", ledger)
    monkeypatch.setattr(card.data, "REPO_ROOT", tmp_path)

    def failing_run(split, n):
        raise card.JevCallFailed("boom")

    monkeypatch.setattr(card, "run", failing_run)
    assert card.main(["--split", "test", "--final", "--sample", "5"]) == 1
    assert not ledger.exists() and not (tmp_path / "results").exists()


class _Flagger:
    def __init__(self, flagged):
        self.flagged = flagged

    def score(self, texts):
        return [1.0 if t in self.flagged else 0.0 for t in texts]


def test_card_saves_each_verdict_and_pairs_the_scam_comparison(monkeypatch):
    meta = {"lures": [], "scam_type": "other"}
    rows = {"scams": [("s1", 1, meta), ("s2", 1, meta)], "ordinary": [("o1", 0, {})], "old_spam": [("x1", 1, {})]}
    verdicts = {"s1": engine.LIKELY_SCAM, "s2": engine.LOOKS_ORDINARY, "o1": engine.LOOKS_ORDINARY,
                "x1": engine.BE_CAREFUL}
    monkeypatch.setattr(card, "groups", lambda split, n: rows)
    monkeypatch.setattr(engine, "check", lambda t: _result(verdicts[t]))
    flaggers = {name: (_Flagger({"s2"}), 0.5) for name in ("keyword_rules", "tfidf_logreg", "tfidf_in_domain")}
    monkeypatch.setattr(card, "_baseline_flaggers", lambda: flaggers)

    result, per_message = card.run("val", None, stop_on_jev_error=True)
    assert [(m["group"], m["verdict"], m["caught"], m["tfidf_logreg_flagged"]) for m in per_message] == [
        ("scams", engine.LIKELY_SCAM, True, False), ("scams", engine.LOOKS_ORDINARY, False, True),
        ("ordinary", engine.LOOKS_ORDINARY, False, False), ("old_spam", engine.BE_CAREFUL, True, False)]
    assert result["groups"]["scams"]["checker_vs_tfidf_logreg_caught"]["diff"] == 0.0
    assert "paired bootstrap" in card.render(result)
