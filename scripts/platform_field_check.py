"""Dump field names and fill rates for iNaturalist, Observation.org and eBird records.

What it does (public APIs only, no keys or logins):
  1. iNaturalist: pulls raw records straight from the iNaturalist API.
  2. GBIF: pulls the copies of iNaturalist, Observation.org and eBird data that GBIF holds.
     (GBIF versions are processed and may drop some native fields.)
For each source and species it counts how often every field is filled, then writes
CSV files and a single zip you can attach.

Run from PowerShell:
    python scripts\\platform_field_check.py
    python scripts\\platform_field_check.py --n 200      # more records per species
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests

USER_AGENT = "fyp-citizen-science-dq/0.1 (field survey script)"
INAT_API = "https://api.inaturalist.org/v1"
GBIF_API = "https://api.gbif.org/v1"
MAX_DEPTH = 6
PAUSE = 1.0  # seconds between requests, to be polite

# Short label -> scientific name
TAXA = {
    "langur": "Presbytis femoralis",
    "pangolin": "Manis javanica",
    "hornbill": "Anthracoceros albirostris",
    "bulbul": "Pycnonotus zeylanicus",
    "miss_joaquim": "Papilionanthe Miss Joaquim",
    "rafflesia": "Rafflesia arnoldii",
    "bougainvillea": "Bougainvillea spectabilis",
}

# GBIF dataset keys (checked against the dataset title at run time).
GBIF_DATASETS = {
    "gbif_inaturalist": ("50c9509d-22c7-4a22-a47d-8c48425ef4a7", "inaturalist"),  # iNaturalist Research-grade Observations 
    "gbif_observation_org": ("8a863029-f435-446a-821e-275f4f641165", "observation.org"),  # Nature data from around the World
    "gbif_ebird": ("4fa7b334-ce0d-4e88-aaae-2e0c138d049e", "ebird"),  # eBird Observation Dataset
}

LOG: list[str] = []


def log(message: str) -> None:
    print(message, flush=True)
    LOG.append(message)


def get_json(url: str, params: dict[str, Any] | None = None, tries: int = 4) -> Any:
    """GET with simple retry/backoff. Returns parsed JSON or raises."""
    for attempt in range(1, tries + 1):
        try:
            response = requests.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=60
            )
            if response.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {response.status_code}")
            response.raise_for_status()
            time.sleep(PAUSE)
            return response.json()
        except Exception as exc:  # noqa: BLE001 - we log and retry
            if attempt == tries:
                raise
            wait = 3 * attempt
            log(f"    retry {attempt}/{tries - 1} after error ({exc}); waiting {wait}s")
            time.sleep(wait)


# ---------- field flattening ----------

def is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def flatten(obj: Any, prefix: str = "", depth: int = 0, out: dict[str, list] | None = None) -> dict[str, list]:
    """Return {field_path: [filled?, example]} for one record.

    Lists of objects are written as 'path[]'. A field counts as filled if any
    element has a non-empty value.
    """
    if out is None:
        out = {}

    def put(path: str, value: Any) -> None:
        filled = not is_empty(value)
        entry = out.setdefault(path, [False, ""])
        if filled and not entry[0]:
            entry[0] = True
            entry[1] = str(value)[:60]

    if depth > MAX_DEPTH:
        put(prefix, obj)
    elif isinstance(obj, dict):
        if not obj:
            put(prefix, obj)
        for key, value in obj.items():
            flatten(value, f"{prefix}.{key}" if prefix else str(key), depth + 1, out)
    elif isinstance(obj, list):
        if not obj or all(not isinstance(item, (dict, list)) for item in obj):
            put(prefix, obj)
        else:
            for item in obj:
                flatten(item, f"{prefix}[]", depth + 1, out)
    else:
        put(prefix, obj)
    return out


class Stats:
    """Fill-rate tally for one source."""

    def __init__(self) -> None:
        self.filled: dict[str, Counter] = defaultdict(Counter)  # field -> taxon -> filled count
        self.examples: dict[str, str] = {}
        self.totals: Counter = Counter()  # taxon -> records seen
        self.issues: Counter = Counter()  # GBIF issue flags

    def add(self, taxon: str, record: dict) -> None:
        self.totals[taxon] += 1
        for path, (filled, example) in flatten(record).items():
            self.filled[path]  # make sure the field is listed even if never filled
            if filled:
                self.filled[path][taxon] += 1
                self.examples.setdefault(path, example)
        for issue in record.get("issues", []) or []:
            self.issues[issue] += 1

    def write_csv(self, path: Path) -> None:
        taxa = [t for t in TAXA if self.totals[t] > 0]
        grand_total = sum(self.totals.values())
        rows = []
        for field, per_taxon in self.filled.items():
            n_filled = sum(per_taxon.values())
            row = {
                "field": field,
                "filled_pct_overall": round(100 * n_filled / grand_total, 1) if grand_total else 0,
            }
            for t in taxa:
                row[f"pct_{t}"] = round(100 * per_taxon[t] / self.totals[t], 1)
            row["example"] = self.examples.get(field, "")
            rows.append(row)
        rows.sort(key=lambda r: (-r["filled_pct_overall"], r["field"]))
        header = ["field", "filled_pct_overall", *[f"pct_{t}" for t in taxa], "example"]
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=header)
            writer.writeheader()
            writer.writerows(rows)


# ---------- iNaturalist (raw API) ----------

def inat_taxon_id(name: str) -> tuple[int, str] | None:
    taxa = get_json(f"{INAT_API}/taxa", {"q": name, "per_page": 10}).get("results", [])
    if not taxa:
        return None
    exact = next((t for t in taxa if t.get("name") == name), None)
    chosen = exact or taxa[0]
    note = "" if exact else f" (NO exact match; used '{chosen.get('name')}')"
    return int(chosen["id"]), note


def fetch_inat(taxon_id: int, n: int) -> tuple[list[dict], int]:
    records: list[dict] = []
    page, total = 1, 0
    while len(records) < n:
        per_page = min(200, n - len(records))
        data = get_json(
            f"{INAT_API}/observations",
            {"taxon_id": taxon_id, "per_page": per_page, "page": page, "order_by": "created_at", "order": "desc"},
        )
        total = data.get("total_results", total)
        results = data.get("results", [])
        if not results:
            break
        records.extend(results)
        if len(results) < per_page:
            break
        page += 1
    return records[:n], total


# ---------- GBIF ----------

def gbif_taxon_key(name: str) -> tuple[int, str] | None:
    match = get_json(f"{GBIF_API}/species/match", {"name": name})
    key = match.get("usageKey")
    if not key:
        return None
    return int(key), f"{match.get('canonicalName')} [{match.get('matchType')}]"


def fetch_gbif(dataset_key: str, taxon_key: int, n: int) -> tuple[list[dict], int]:
    records: list[dict] = []
    offset, total = 0, 0
    while len(records) < n:
        limit = min(300, n - len(records))
        data = get_json(
            f"{GBIF_API}/occurrence/search",
            {"datasetKey": dataset_key, "taxonKey": taxon_key, "limit": limit, "offset": offset},
        )
        total = data.get("count", total)
        results = data.get("results", [])
        records.extend(results)
        if data.get("endOfRecords", True) or not results:
            break
        offset += limit
    return records[:n], total


def check_gbif_dataset(label: str, key: str, expect: str) -> bool:
    try:
        title = get_json(f"{GBIF_API}/dataset/{key}").get("title", "")
    except Exception as exc:  # noqa: BLE001
        log(f"  WARNING: could not look up GBIF dataset {key} for {label}: {exc}")
        return False
    log(f"  {label}: GBIF dataset key {key} is titled '{title}'")
    if expect not in title.lower():
        log(f"  WARNING: that title does not mention '{expect}'. Skipping {label}. "
            f"Find the right key at https://www.gbif.org/dataset/search and pass it with --key-{label}")
        return False
    return True


# ---------- main ----------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=100, help="records per species per source (default 100)")
    parser.add_argument("--out", default="platform_check_output", help="output folder")
    for label, (key, _) in GBIF_DATASETS.items():
        parser.add_argument(f"--key-{label}", default=key, help=f"GBIF dataset key for {label}")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: list[dict] = []
    samples: dict[str, list] = {}
    all_stats: dict[str, Stats] = {}

    try:
        # 1. iNaturalist, raw
        log("== iNaturalist (raw API) ==")
        stats = all_stats["inaturalist_raw"] = Stats()
        for label, name in TAXA.items():
            try:
                found = inat_taxon_id(name)
                if not found:
                    log(f"  {label}: no iNaturalist taxon found for '{name}'")
                    counts.append({"source": "inaturalist_raw", "species": label, "retrieved": 0, "available": 0, "note": "taxon not found"})
                    continue
                taxon_id, note = found
                records, available = fetch_inat(taxon_id, args.n)
                log(f"  {label}: {len(records)} of {available} records{note}")
                for record in records:
                    stats.add(label, record)
                if records:
                    samples.setdefault("inaturalist_raw", []).extend(records[:1])
                counts.append({"source": "inaturalist_raw", "species": label, "retrieved": len(records), "available": available, "note": note.strip()})
            except Exception as exc:  # noqa: BLE001
                log(f"  {label}: FAILED ({exc})")
                counts.append({"source": "inaturalist_raw", "species": label, "retrieved": 0, "available": "", "note": f"error: {exc}"})

        # 2. GBIF copies
        taxon_keys: dict[str, tuple[int, str] | None] = {}
        for label, name in TAXA.items():
            try:
                taxon_keys[label] = gbif_taxon_key(name)
            except Exception as exc:  # noqa: BLE001
                log(f"  GBIF name match failed for {name}: {exc}")
                taxon_keys[label] = None

        for source, (_, expect) in GBIF_DATASETS.items():
            key = getattr(args, f"key_{source}")
            log(f"== {source} (via GBIF) ==")
            if not check_gbif_dataset(source, key, expect):
                continue
            stats = all_stats[source] = Stats()
            for label, name in TAXA.items():
                match = taxon_keys.get(label)
                if not match:
                    log(f"  {label}: '{name}' not found in GBIF taxonomy")
                    counts.append({"source": source, "species": label, "retrieved": 0, "available": 0, "note": "not in GBIF taxonomy"})
                    continue
                try:
                    records, available = fetch_gbif(key, match[0], args.n)
                    log(f"  {label}: {len(records)} of {available} records (matched {match[1]})")
                    for record in records:
                        stats.add(label, record)
                    if records:
                        samples.setdefault(source, []).extend(records[:1])
                    counts.append({"source": source, "species": label, "retrieved": len(records), "available": available, "note": match[1]})
                except Exception as exc:  # noqa: BLE001
                    log(f"  {label}: FAILED ({exc})")
                    counts.append({"source": source, "species": label, "retrieved": 0, "available": "", "note": f"error: {exc}"})
    finally:
        # Always write whatever we have, even if something failed half-way.
        for source, stats in all_stats.items():
            stats.write_csv(out_dir / f"{source}_fields.csv")
        with (out_dir / "record_counts.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=["source", "species", "retrieved", "available", "note"])
            writer.writeheader()
            writer.writerows(counts)
        with (out_dir / "gbif_issue_flags.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["source", "issue_flag", "records"])
            for source, stats in all_stats.items():
                for issue, count in stats.issues.most_common():
                    writer.writerow([source, issue, count])
        (out_dir / "sample_records.json").write_text(json.dumps(samples, indent=1, default=str), encoding="utf-8")
        (out_dir / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")

        zip_path = Path(f"{args.out}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(out_dir.iterdir()):
                archive.write(file, arcname=file.name)
        print(f"\nDone. Attach this file: {zip_path.resolve()}")


if __name__ == "__main__":
    sys.exit(main())
