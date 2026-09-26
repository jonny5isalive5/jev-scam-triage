"""
The live Jev path, exercised offline: the real typesafe-sdk client with a
fake HTTP transport. Skipped when typesafe-sdk isn't installed.
"""

import json

import pytest

typesafe_sdk = pytest.importorskip("typesafe_sdk")
httpx2 = pytest.importorskip("httpx2")

from scam_triage import engine, jev_client  # noqa: E402
from scam_triage.questions import ORGANISATION_TYPES, QUESTIONS  # noqa: E402


def _client(handler):
    return typesafe_sdk.TypeSafeClient(
        api_key="test-key-not-real",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        retry=typesafe_sdk.RetryPolicy(max_retries=0),
    )


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key-not-real")
    monkeypatch.setattr(jev_client, "_client", None)


def test_live_request_carries_only_the_masked_message_and_answers_parse(live, monkeypatch):
    sent = {}

    def handler(request):
        sent.update(json.loads(request.content))
        answers = {n: {"type": "noul", "noul": 0.9} for n, q in QUESTIONS.items() if q["type"] == "noul"}
        probs = {k: (0.8 if k == "delivery" else 0.2 / (len(ORGANISATION_TYPES) - 1)) for k in ORGANISATION_TYPES}
        answers["claims_to_be"] = {"type": "choice", "choice": "delivery", "confidence": 0.8, "probabilities": probs}
        return httpx2.Response(200, json={"model": "jev-latest", "usage": {}, "answers": answers})

    monkeypatch.setattr(jev_client, "_client", _client(handler))
    result = engine.check("Parcel held: pay £1.45 at https://evri-fee.info, code 123456")
    assert result.mode == "live" and result.jev_used and result.verdict == engine.LIKELY_SCAM
    assert sent["state"] == {"message": "Parcel held: pay £1.45 at <URL>, code <NUMBER>"}
    assert set(sent["questions"]) == set(QUESTIONS)


def test_api_error_falls_back_to_code_checks(live, monkeypatch):
    monkeypatch.setattr(jev_client, "_client", _client(lambda request: httpx2.Response(401, json={"error": "bad key"})))
    result = engine.check("Hello, is this still available?")
    assert result.verdict == engine.BE_CAREFUL and not result.jev_used and result.error
