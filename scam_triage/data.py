"""
Dataset loading, de-duplication and the fixed dev/val/test split.

Every dataset is a list of (text, label) pairs with label 1 = scam/spam,
0 = legitimate. Datasets are registered in DATASETS with a pinned
SHA-256, so a changed upstream file is an error rather than a silent
change to every number downstream.

Splitting happens AFTER collapsing near-duplicates (same text once
digits and URLs are masked). Spam campaigns resend one template with
different phone numbers; a plain random split puts copies of the same
message in both training and test, which inflates every score.
"""

import hashlib
import json
import random
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SPLITS_DIR = REPO_ROOT / "splits"

SPLIT_SEED = 20260926
SPLIT_FRACTIONS = {"dev": 0.6, "val": 0.2, "test": 0.2}


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    url: str
    sha256: str
    citation: str
    license_note: str
    positive_label: str  # the raw label string that maps to 1


DATASETS = {
    "sms_spam": DatasetSpec(
        name="sms_spam",
        # GitHub mirror of the UCI SMS Spam Collection (5,574 messages). The
        # original host is https://archive.ics.uci.edu/dataset/228/sms+spam+collection
        url="https://raw.githubusercontent.com/justmarkham/pycon-2016-tutorial/master/data/sms.tsv",
        sha256="7d039a24a6083ed9ef0f806ebad56bbb976e3aeb8de05669173bfdc4996c239d",
        citation=(
            "Almeida, T.A., Gomez Hidalgo, J.M., Yamakami, A. Contributions to the Study of "
            "SMS Spam Filtering: New Collection and Results. DocEng 2011."
        ),
        license_note="Listed by UCI under CC BY 4.0 -- verify before redistributing.",
        positive_label="spam",
    ),
}


def dataset_path(name: str) -> Path:
    return DATA_DIR / f"{name}.tsv"


def download(name: str) -> Path:
    """Fetch the dataset if absent and verify its pinned hash."""
    spec = DATASETS[name]
    path = dataset_path(name)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(spec.url, timeout=60) as resp:
            path.write_bytes(resp.read())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != spec.sha256:
        raise ValueError(
            f"{path} has SHA-256 {digest}, expected {spec.sha256}. The upstream file changed; "
            "re-pin it deliberately rather than letting every result shift silently."
        )
    return path


def load_raw(name: str) -> list[tuple[str, int]]:
    spec = DATASETS[name]
    rows = []
    for line in download(name).read_text(encoding="utf-8").splitlines():
        label, text = line.split("\t", 1)
        rows.append((text, int(label == spec.positive_label)))
    return rows


def normalize_key(text: str) -> str:
    """Near-duplicate key: lowercase, URLs and digits masked, punctuation dropped."""
    t = text.lower()
    t = re.sub(r"https?://\S+|www\.\S+", "<url>", t)
    t = re.sub(r"\d+", "#", t)
    t = re.sub(r"[^a-z#<> ]", " ", t)
    return " ".join(t.split())


def message_id(text: str) -> str:
    return hashlib.sha256(normalize_key(text).encode("utf-8")).hexdigest()[:16]


def dedupe(rows: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """Keep the first message per near-duplicate key. Conflicting labels are an error."""
    seen: dict[str, int] = {}
    out = []
    for text, label in rows:
        key = normalize_key(text)
        if key in seen:
            if seen[key] != label:
                raise ValueError(f"Near-duplicate messages with conflicting labels: {text!r}")
            continue
        seen[key] = label
        out.append((text, label))
    return out


def make_split_manifest(name: str, seed: int = SPLIT_SEED) -> dict:
    """Stratified split of the de-duplicated data, recorded as message ids only (no text)."""
    rows = dedupe(load_raw(name))
    rng = random.Random(seed)
    manifest = {"dataset": name, "sha256": DATASETS[name].sha256, "seed": seed, "splits": {}}
    by_label = {0: [], 1: []}
    for text, label in rows:
        by_label[label].append(message_id(text))
    for ids in by_label.values():
        rng.shuffle(ids)
    for split in SPLIT_FRACTIONS:
        manifest["splits"][split] = []
    for ids in by_label.values():
        n_dev = round(len(ids) * SPLIT_FRACTIONS["dev"])
        n_val = round(len(ids) * SPLIT_FRACTIONS["val"])
        manifest["splits"]["dev"] += ids[:n_dev]
        manifest["splits"]["val"] += ids[n_dev:n_dev + n_val]
        manifest["splits"]["test"] += ids[n_dev + n_val:]
    for split in manifest["splits"]:
        manifest["splits"][split].sort()
    return manifest


def manifest_path(name: str) -> Path:
    return SPLITS_DIR / f"{name}.json"


def write_manifest(name: str) -> Path:
    """Create the split manifest once. Refuses to overwrite: the split is fixed forever."""
    path = manifest_path(name)
    if path.exists():
        raise FileExistsError(f"{path} already exists; the split is frozen. Delete it only to start over.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(make_split_manifest(name), indent=1) + "\n")
    return path


def load_split(name: str, split: str) -> list[tuple[str, int]]:
    """Messages for one split, as recorded in the committed manifest."""
    manifest = json.loads(manifest_path(name).read_text())
    if manifest["sha256"] != DATASETS[name].sha256:
        raise ValueError("Split manifest was built from a different dataset file.")
    wanted = set(manifest["splits"][split])
    rows = [(t, y) for t, y in dedupe(load_raw(name)) if message_id(t) in wanted]
    if len(rows) != len(wanted):
        raise ValueError(f"Manifest lists {len(wanted)} {split} messages but {len(rows)} were found.")
    return rows
