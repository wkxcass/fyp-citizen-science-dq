"""Download a small, normalized occurrence extract from iNaturalist."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import requests

API = "https://api.inaturalist.org/v1"
FIELDS = ["observation_id", "taxon_name", "latitude", "longitude", "observed_on", "quality_grade", "observer_login", "observation_url"]


def find_taxon_id(scientific_name: str, timeout: int = 30) -> int:
    response = requests.get(f"{API}/taxa", params={"q": scientific_name, "per_page": 10}, headers={"User-Agent": "fyp-citizen-science-dq/0.1"}, timeout=timeout)
    response.raise_for_status()
    taxa = response.json().get("results", [])
    taxon = next((item for item in taxa if item.get("name") == scientific_name), None) or (taxa[0] if taxa else None)
    if not taxon:
        raise RuntimeError(f"Could not find an iNaturalist taxon for {scientific_name!r}.")
    return int(taxon["id"])


def fetch_observations(taxon_id: int, per_page: int = 100, timeout: int = 30) -> list[dict[str, Any]]:
    response = requests.get(f"{API}/observations", params={"taxon_id": taxon_id, "per_page": per_page, "page": 1, "order_by": "created_at", "order": "desc"}, headers={"User-Agent": "fyp-citizen-science-dq/0.1"}, timeout=timeout)
    response.raise_for_status()
    return response.json().get("results", [])


def normalize(observation: dict[str, Any]) -> dict[str, Any]:
    coordinates = observation.get("geojson", {}).get("coordinates", [None, None])
    obs_id = observation.get("id")
    return {"observation_id": obs_id, "taxon_name": (observation.get("taxon") or {}).get("name"), "latitude": coordinates[1], "longitude": coordinates[0], "observed_on": observation.get("observed_on"), "quality_grade": observation.get("quality_grade"), "observer_login": (observation.get("user") or {}).get("login"), "observation_url": f"https://www.inaturalist.org/observations/{obs_id}"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taxon", default="Presbytis femoralis")
    parser.add_argument("--output", default="data/raw/occurrences.csv")
    parser.add_argument("--per-page", type=int, default=100)
    args = parser.parse_args()
    taxon_id = find_taxon_id(args.taxon)
    rows = [normalize(item) for item in fetch_observations(taxon_id, args.per_page)]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} observations to {output} (taxon id {taxon_id}).")


if __name__ == "__main__":
    main()
