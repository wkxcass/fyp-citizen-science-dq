"""Download a small, normalized occurrence extract from iNaturalist."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import requests

from src.project_config import load_config, resolve_path
from src.qc_engine.schema import normalize_observation, schema_column_names

API = "https://api.inaturalist.org/v1"
def find_taxon_id(scientific_name: str, api_base_url: str = API, timeout: int = 30) -> int:
    response = requests.get(f"{api_base_url.rstrip('/')}/taxa", params={"q": scientific_name, "per_page": 10}, headers={"User-Agent": "fyp-citizen-science-dq/0.1"}, timeout=timeout)
    response.raise_for_status()
    taxa = response.json().get("results", [])
    taxon = next((item for item in taxa if item.get("name") == scientific_name), None) or (taxa[0] if taxa else None)
    if not taxon:
        raise RuntimeError(f"Could not find an iNaturalist taxon for {scientific_name!r}.")
    return int(taxon["id"])


def fetch_observations(taxon_id: int, per_page: int = 100, api_base_url: str = API, timeout: int = 30) -> list[dict[str, Any]]:
    response = requests.get(f"{api_base_url.rstrip('/')}/observations", params={"taxon_id": taxon_id, "per_page": per_page, "page": 1, "order_by": "created_at", "order": "desc"}, headers={"User-Agent": "fyp-citizen-science-dq/0.1"}, timeout=timeout)
    response.raise_for_status()
    return response.json().get("results", [])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/v0.yaml")
    parser.add_argument("--taxon")
    parser.add_argument("--output")
    parser.add_argument("--per-page", type=int)
    args = parser.parse_args()
    config, repo_root = load_config(args.config)
    if config["dataset"]["platform"].lower() != "inaturalist":
        raise SystemExit("This adapter requires dataset.platform to be iNaturalist.")
    taxon = args.taxon or config["species"]["scientific_name"]
    per_page = args.per_page or config["dataset"]["fetch"]["per_page"]
    output = Path(args.output) if args.output else resolve_path(repo_root, config["dataset"]["input_path"])
    api_base_url = config["dataset"]["api_base_url"]
    taxon_id = find_taxon_id(taxon, api_base_url=api_base_url)
    rows = [normalize_observation(item, config) for item in fetch_observations(taxon_id, per_page, api_base_url=api_base_url)]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=schema_column_names(config))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} observations to {output} (taxon id {taxon_id}).")


if __name__ == "__main__":
    main()
