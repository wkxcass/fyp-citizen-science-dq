"""Download iNaturalist occurrences with public API responses and retrieval metadata."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.project_config import load_config, resolve_path, USER_AGENT
from src.qc_engine.schema import normalize_observation, schema_column_names

MAX_PAGE_SIZE = 200  # iNaturalist API ceiling for per_page on /observations
API = "https://api.inaturalist.org/v1"


def _get_json(
    url: str,
    params: dict[str, Any],
    timeout: int,
    response_log: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if response_log is not None:
        response_log.append({
            "url": url,
            "params": params,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "response": payload,
        })
    return payload


def find_taxon_id(
    scientific_name: str,
    api_base_url: str = API,
    timeout: int = 30,
    *,
    response_log: list[dict[str, Any]] | None = None,
) -> int:
    payload = _get_json(
        f"{api_base_url.rstrip('/')}/taxa",
        {"q": scientific_name, "per_page": 10},
        timeout,
        response_log,
    )
    taxa = payload.get("results", [])
    taxon = next((item for item in taxa if item.get("name") == scientific_name), None) or (taxa[0] if taxa else None)
    if not taxon:
        raise RuntimeError(f"Could not find an iNaturalist taxon for {scientific_name!r}.")
    return int(taxon["id"])


def fetch_observations(
    taxon_id: int,
    total_records: int,
    api_base_url: str = API,
    timeout: int = 30,
    *,
    response_log: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Page through the iNaturalist API until total_records is reached or results run out."""
    if total_records <= 0:
        raise ValueError("total_records must be greater than zero.")
    observations: list[dict[str, Any]] = []
    page = 1
    # Changing per_page between requests changes the API's page offsets.
    per_page = min(MAX_PAGE_SIZE, total_records)
    while len(observations) < total_records:
        payload = _get_json(
            f"{api_base_url.rstrip('/')}/observations",
            {"taxon_id": taxon_id, "per_page": per_page, "page": page, "order_by": "created_at", "order": "desc"},
            timeout,
            response_log,
        )
        results = payload.get("results", [])
        if not results:
            break  # no more pages available
        observations.extend(results)
        if len(results) < per_page:
            break  # that was the last page
        page += 1
    return observations[:total_records]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    parser.add_argument("--taxon")
    parser.add_argument("--output")
    parser.add_argument("--total-records", type=int)
    args = parser.parse_args()
    config, repo_root = load_config(args.config)
    if config["dataset"]["platform"].lower() != "inaturalist":
        raise SystemExit("This adapter requires dataset.platform to be iNaturalist.")
    taxon = args.taxon or config["species"]["scientific_name"]
    total_records = args.total_records if args.total_records is not None else config["dataset"]["fetch"]["total_records"]
    if total_records <= 0:
        parser.error("total-records must be greater than zero.")
    output = Path(args.output) if args.output else resolve_path(repo_root, config["dataset"]["input_path"])
    raw_output = output.with_suffix(".raw.json")
    metadata_output = output.with_suffix(".metadata.json")
    api_base_url = config["dataset"].get("api_base_url", API).rstrip("/")
    response_log: list[dict[str, Any]] = []
    started_at = datetime.now(timezone.utc).isoformat()
    taxon_id = find_taxon_id(taxon, api_base_url=api_base_url, response_log=response_log)
    observations = fetch_observations(taxon_id, total_records, api_base_url=api_base_url, response_log=response_log)
    completed_at = datetime.now(timezone.utc).isoformat()
    resolved_taxon = next(item for item in response_log[0]["response"]["results"] if int(item["id"]) == taxon_id)
    rows = [normalize_observation(item, config) for item in observations]
    metadata = {
        "retrieval_started_at_utc": started_at,
        "retrieval_completed_at_utc": completed_at,
        "requested_taxon": taxon,
        "resolved_taxon": {"id": taxon_id, "name": resolved_taxon.get("name")},
        "requested_record_count": total_records,
        "actual_record_count": len(rows),
        "api_base_url": api_base_url,
        "requests": [{key: value for key, value in entry.items() if key != "response"} for entry in response_log],
        "observation_ids": [item["id"] for item in observations],
        "schema": config["dataset"]["schema"],
        "files": {"csv": output.name, "raw": raw_output.name},
    }
    # Fetching and normalization finish before existing snapshot files are touched.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=schema_column_names(config))
        writer.writeheader()
        writer.writerows(rows)
    raw_output.write_text(json.dumps({"responses": response_log}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    metadata_output.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} observations to {output} (taxon id {taxon_id}).")
    print(f"Public API responses: {raw_output}")
    print(f"Retrieval metadata: {metadata_output}")


if __name__ == "__main__":
    main()
