import json

import pytest

from scam_triage import data


def test_normalize_key_masks_digits_and_urls():
    a = data.normalize_key("WIN £500! Call 09061701461 now http://x.co/abc")
    b = data.normalize_key("win £900! call 09099726429 NOW www.y.com")
    assert a == b


def test_dedupe_keeps_first_and_rejects_conflicting_labels():
    rows = [("Call 0800 123", 1), ("call 0800 999", 1), ("hello", 0)]
    assert data.dedupe(rows) == [("Call 0800 123", 1), ("hello", 0)]
    with pytest.raises(ValueError):
        data.dedupe([("same text 1", 1), ("same text 2", 0)])


def test_committed_manifest_splits_are_disjoint_and_complete():
    manifest = json.loads(data.manifest_path("sms_spam").read_text())
    ids = {name: set(v) for name, v in manifest["splits"].items()}
    assert not ids["dev"] & ids["val"]
    assert not ids["dev"] & ids["test"]
    assert not ids["val"] & ids["test"]
    assert manifest["sha256"] == data.DATASETS["sms_spam"].sha256


def test_manifest_is_frozen():
    with pytest.raises(FileExistsError):
        data.write_manifest("sms_spam")


@pytest.mark.skipif(not data.dataset_path("sms_spam").exists(), reason="dataset not downloaded")
def test_manifest_reproduces_from_the_pinned_file():
    committed = json.loads(data.manifest_path("sms_spam").read_text())
    assert data.make_split_manifest("sms_spam") == committed
