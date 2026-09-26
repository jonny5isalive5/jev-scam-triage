from scam_triage import metrics


def test_summarize_counts():
    s = metrics.summarize([1, 1, 0, 0], [True, False, True, False])
    assert (s["tp"], s["fn"], s["fp"], s["tn"]) == (1, 1, 1, 1)
    assert s["recall"] == 0.5 and s["fpr"] == 0.5


def test_pick_threshold_respects_the_fpr_budget():
    labels = [0] * 100 + [1] * 10
    scores = [i / 100 for i in range(100)] + [0.5 + i / 100 for i in range(10)]
    thr = metrics.pick_threshold(labels, scores, max_fpr=0.01)
    preds = [s >= thr for s in scores]
    assert metrics.summarize(labels, preds)["fpr"] <= 0.01


def test_pick_threshold_flags_nothing_when_budget_cannot_be_met():
    thr = metrics.pick_threshold([0, 0, 1], [0.9, 0.8, 0.1], max_fpr=0.0)
    assert thr == 0.9 or thr == float("inf")
    assert metrics.summarize([0, 0, 1], [s >= thr for s in [0.9, 0.8, 0.1]])["fpr"] == 0.0


def test_paired_bootstrap_interval_contains_point_estimate():
    labels = [1] * 50 + [0] * 50
    a = [True] * 45 + [False] * 5 + [False] * 50
    b = [True] * 30 + [False] * 20 + [False] * 50
    cmp = metrics.paired_bootstrap(labels, a, b, metric="recall", n=500)
    assert cmp["ci_low"] <= cmp["diff"] <= cmp["ci_high"]
    assert cmp["ci_low"] > 0
