from scam_triage import spec


def test_committed_spec_is_up_to_date():
    assert spec.SPEC_PATH.read_text(encoding="utf-8") == spec.render(), (
        "spec/scam_check_spec.json is stale -- run: python -m scam_triage.spec"
    )


def test_golden_cases_cover_every_verdict():
    verdicts = {case["expected"]["verdict"] for case in spec.build()["golden"]}
    assert verdicts == {"likely_scam", "be_careful", "looks_ordinary"}
