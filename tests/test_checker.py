import pytest

from scam_triage import card, data, engine, jev_client
from scam_triage.gate import gate_reasons, mixed_script_words
from scam_triage.links import extract_links, registrable_domain
from scam_triage.mask import mask_for_jev
from scam_triage.web import render_result


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)


def test_lookalike_domain_is_caught_and_official_domain_is_not():
    (fake,) = extract_links("pay at https://royalmail-redelivery.info/fee")
    assert fake.lookalike_of == "royalmail"
    (real,) = extract_links("track at https://www.royalmail.com/track-your-item")
    assert real.lookalike_of is None
    (gov,) = extract_links("claim at hmrc-gov-refund.com")
    assert gov.lookalike_of in {"hmrc", "government"}


def test_shortener_and_registrable_domain():
    (link,) = extract_links("see bit.ly/3abc")
    assert link.shortener
    assert registrable_domain("secure.login.barclays.co.uk") == "barclays.co.uk"


def test_masking_hides_codes_contacts_and_links_but_keeps_amounts():
    masked = mask_for_jev("Your code is 482913. Pay £1.45 at https://x.info or call 07700 900123, a@b.com")
    assert "482913" not in masked and "07700" not in masked and "a@b.com" not in masked
    assert "https://x.info" not in masked and "£1.45" in masked
    assert {"<NUMBER>", "<URL>", "<PHONE_NUMBER>", "<EMAIL_ADDRESS>"} <= set(masked.replace(".", " ").replace(",", " ").split())


def test_gate_rules():
    assert gate_reasons("see you at 6") == []
    assert "link" in gate_reasons("look at www.example.com")
    assert "unknown_sender" in gate_reasons("hello", sender_known=False)
    assert mixed_script_words("Ηello аll") and not mixed_script_words("Hello all")


def test_background_mode_skips_ordinary_messages_without_calling_jev(monkeypatch):
    monkeypatch.setattr(jev_client, "ask", lambda state: pytest.fail("Jev should not be called"))
    result = engine.check("see you at 6", force=False)
    assert result.verdict == engine.LOOKS_ORDINARY and not result.jev_used


def test_jev_receives_only_the_masked_message(monkeypatch):
    seen = {}

    def fake_ask(state):
        seen.update(state)
        return jev_client._mock_answers(state["message"])

    monkeypatch.setattr(jev_client, "ask", fake_ask)
    engine.check("Code 482913 from https://paypal-help.xyz")
    assert set(seen) == {"message"}
    assert "482913" not in seen["message"] and "paypal-help" not in seen["message"]


def test_lookalike_link_alone_makes_it_likely_scam_even_if_jev_is_down(monkeypatch):
    def down(state):
        raise jev_client.JevUnavailable("timeout")

    monkeypatch.setattr(jev_client, "ask", down)
    result = engine.check("Your parcel: https://royalmail-fees.info")
    assert result.verdict == engine.LIKELY_SCAM and result.error == "timeout"
    assert engine.check("hello there").verdict == engine.BE_CAREFUL  # can't check -> never "looks ordinary"


def test_examples_in_mock_mode():
    scam = engine.check("URGENT: your account is locked. Verify within 2 hours at https://hsbc-secure.xyz")
    assert scam.verdict == engine.LIKELY_SCAM
    assert engine.check("running 10 mins late, see you at the cafe").verdict == engine.LOOKS_ORDINARY


def test_web_output_escapes_html():
    result = engine.Result(engine.LIKELY_SCAM, ["<script>x</script>"], "a & b", [], True, "mock")
    html = render_result(result)
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_imc_placeholders_are_filled_except_the_ones_masking_also_produces():
    out = data.fill_placeholders("Hi <NAMED_ENTITY>, pay by <DATE_TIME> at <URL> ref <US_BANK_NUMBER>")
    assert out == "Hi Alex, pay by today at <URL> ref <NUMBER>"


def test_kappa():
    assert card._kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert card._kappa([True, True, False, False], [True, False, True, False]) == 0.0
