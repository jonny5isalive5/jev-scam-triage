"""Metrics, the fixed operating-point rule, and a paired bootstrap for comparisons."""

import random

# The operating point every system is judged at: the lowest threshold whose
# false-positive rate on validation is at most this. Flagging a real message
# as a scam is the costly error for someone reading their own texts.
MAX_FPR = 0.01


def confusion(labels, preds):
    tp = sum(1 for y, p in zip(labels, preds) if y and p)
    fp = sum(1 for y, p in zip(labels, preds) if not y and p)
    fn = sum(1 for y, p in zip(labels, preds) if y and not p)
    tn = sum(1 for y, p in zip(labels, preds) if not y and not p)
    return tp, fp, fn, tn


def summarize(labels, preds) -> dict:
    tp, fp, fn, tn = confusion(labels, preds)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "fpr": fpr, "f1": f1}


def pick_threshold(labels, scores, max_fpr: float = MAX_FPR) -> float:
    """
    Lowest threshold (flag if score >= threshold) with FPR <= max_fpr, i.e.
    the highest recall allowed under the false-alarm budget. Chosen on the
    validation split only.
    """
    candidates = sorted(set(scores), reverse=True)
    best = float("inf")  # flag nothing: FPR 0
    for thr in candidates:
        preds = [s >= thr for s in scores]
        if summarize(labels, preds)["fpr"] <= max_fpr:
            best = thr
        else:
            break
    return best


def paired_bootstrap(labels, preds_a, preds_b, metric: str = "recall", n: int = 2000, seed: int = 0) -> dict:
    """
    95% interval for metric(A) - metric(B) by resampling messages with
    replacement. A difference counts as real only if the interval excludes 0.
    """
    rng = random.Random(seed)
    idx = list(range(len(labels)))
    diffs = []
    for _ in range(n):
        sample = [rng.choice(idx) for _ in idx]
        ys = [labels[i] for i in sample]
        a = summarize(ys, [preds_a[i] for i in sample])[metric]
        b = summarize(ys, [preds_b[i] for i in sample])[metric]
        diffs.append(a - b)
    diffs.sort()
    point = summarize(labels, preds_a)[metric] - summarize(labels, preds_b)[metric]
    return {"metric": metric, "diff": point, "ci_low": diffs[int(0.025 * n)], "ci_high": diffs[int(0.975 * n) - 1]}
