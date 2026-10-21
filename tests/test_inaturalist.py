import csv
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests
import yaml

from src.qc_engine.inaturalist import fetch_observations, main, MAX_PAGE_SIZE
from src.qc_engine.run import run


ROOT = Path(__file__).parents[1]


def _mock_response(results):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": results}
    return response


def test_fetch_observations_pages_until_total_records_reached():
    # total_records requires 2 pages given MAX_PAGE_SIZE-sized batches
    total_records = MAX_PAGE_SIZE + 50
    page_1 = [{"id": i} for i in range(MAX_PAGE_SIZE)]
    page_2 = [{"id": i} for i in range(MAX_PAGE_SIZE, MAX_PAGE_SIZE + 50)]

    with patch("src.qc_engine.inaturalist.requests.get") as mock_get:
        mock_get.side_effect = [_mock_response(page_1), _mock_response(page_2)]
        results = fetch_observations(taxon_id=1, total_records=total_records)

    assert len(results) == total_records
    assert mock_get.call_count == 2


def test_fetch_observations_stops_on_short_final_page():
    # API has fewer observations than total_records; loop should stop, not hang
    total_records = 100
    short_page = [{"id": i} for i in range(30)]

    with patch("src.qc_engine.inaturalist.requests.get") as mock_get:
        mock_get.side_effect = [_mock_response(short_page)]
        results = fetch_observations(taxon_id=1, total_records=total_records)

    assert len(results) == 30
    assert mock_get.call_count == 1


def test_fetch_observations_stops_on_empty_results():
    with patch("src.qc_engine.inaturalist.requests.get") as mock_get:
        mock_get.side_effect = [_mock_response([])]
        results = fetch_observations(taxon_id=1, total_records=100)

    assert results == []
    assert mock_get.call_count == 1


def test_fetch_observations_truncates_to_exact_total_records():
    # If the last page overshoots (shouldn't happen given per_page math, but
    # guards the [:total_records] slice), result length is still exact.
    total_records = 10
    page = [{"id": i} for i in range(15)]

    with patch("src.qc_engine.inaturalist.requests.get") as mock_get:
        mock_get.side_effect = [_mock_response(page)]
        results = fetch_observations(taxon_id=1, total_records=total_records)

    assert len(results) == total_records


def test_page_size_stays_fixed_so_page_offsets_do_not_repeat_records():
    available = [{"id": i} for i in range(500)]

    def api_page(url, *, params, **kwargs):
        start = (params["page"] - 1) * params["per_page"]
        return _mock_response(available[start:start + params["per_page"]])

    responses = []
    with patch("src.qc_engine.inaturalist.requests.get", side_effect=api_page) as get:
        observations = fetch_observations(1, 250, response_log=responses)

    assert observations == available[:250]
    assert [call.kwargs["params"]["per_page"] for call in get.call_args_list] == [200, 200]
    # Preserve the whole response, even when the CSV only needs part of its final page.
    assert responses[1]["response"]["results"] == available[200:400]


def _snapshot_config(tmp_path):
    config = yaml.safe_load((ROOT / "config/v0.1.yaml").read_text(encoding="utf-8"))
    config["dataset"]["input_path"] = "data/raw/pilot/occurrences.csv"
    config["dataset"]["fetch"]["total_records"] = 100
    config["dataset"]["api_base_url"] = "https://example.test/v1/"
    config_path = tmp_path / "config" / "pilot.yaml"
    config_path.parent.mkdir()
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config, config_path


@pytest.mark.parametrize("use_overrides", [False, True])
def test_cli_saves_public_responses_metadata_and_compatible_csv(tmp_path, monkeypatch, use_overrides):
    config, config_path = _snapshot_config(tmp_path)
    output = tmp_path / config["dataset"]["input_path"]
    requested_taxon = config["species"]["scientific_name"]
    requested_count = 100
    argv = ["inaturalist", "--config", str(config_path)]
    if use_overrides:
        output = tmp_path / "override" / "sample.csv"
        requested_taxon = "alternate lookup"
        requested_count = 2
        argv += ["--taxon", requested_taxon, "--total-records", "2", "--output", str(output)]
    monkeypatch.setattr("sys.argv", argv)
    observations = [
        {
            "id": 123,
            "taxon": {"name": "Presbytis femoralis"},
            "geojson": {"coordinates": [103.8, 1.35]},
            "geoprivacy": "obscured",
            "obscured": True,
            "public_positional_accuracy": 28000,
            "captive": False,
            "user": {"login": "observer"},
            "extra_field": {"preserve": "all public fields"},
        },
        {"id": 124, "geojson": {"coordinates": [-0.12, 51.5]}},
    ]
    taxa = _mock_response([{"id": 42, "name": "Presbytis femoralis"}])
    page = _mock_response(observations)
    page.json.return_value.update({"total_results": 2, "page": 1, "per_page": requested_count})
    with patch("src.qc_engine.inaturalist.requests.get", side_effect=[taxa, page]) as get:
        main()

    raw = json.loads(output.with_suffix(".raw.json").read_text(encoding="utf-8"))
    metadata = json.loads(output.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    assert [entry["response"] for entry in raw["responses"]] == [taxa.json.return_value, page.json.return_value]
    assert metadata["requested_taxon"] == requested_taxon
    assert metadata["resolved_taxon"] == {"id": 42, "name": "Presbytis femoralis"}
    assert metadata["requested_record_count"] == requested_count
    assert metadata["actual_record_count"] == 2
    assert metadata["observation_ids"] == [123, 124]
    assert metadata["schema"] == config["dataset"]["schema"]
    assert metadata["files"] == {"csv": output.name, "raw": output.with_suffix(".raw.json").name}
    assert metadata["api_base_url"] == "https://example.test/v1"
    assert metadata["requests"] == [{
        "url": call.args[0], "params": call.kwargs["params"], "retrieved_at_utc": entry["retrieved_at_utc"],
    } for call, entry in zip(get.call_args_list, raw["responses"])]
    assert metadata["requests"][0]["params"] == {"q": requested_taxon, "per_page": 10}
    assert metadata["requests"][1]["params"] == {
        "taxon_id": 42, "per_page": requested_count, "page": 1, "order_by": "created_at", "order": "desc",
    }
    start = datetime.fromisoformat(metadata["retrieval_started_at_utc"])
    end = datetime.fromisoformat(metadata["retrieval_completed_at_utc"])
    assert start.utcoffset().total_seconds() == 0
    assert start <= end
    for entry in raw["responses"]:
        assert entry["url"].startswith("https://example.test/v1/")
        assert start <= datetime.fromisoformat(entry["retrieved_at_utc"]) <= end
    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == [field["name"] for field in config["dataset"]["schema"]["fields"]]
    assert [row["observation_id"] for row in rows] == ["123", "124"]
    assert rows[0]["latitude"] == "1.35"
    assert rows[0]["longitude"] == "103.8"
    assert run(output, ROOT / "src/oracle_gen/example_oracle.py", tmp_path / "flags.csv", schema_config=config) == 1


def test_empty_download_still_saves_auditable_snapshot(tmp_path, monkeypatch):
    config, config_path = _snapshot_config(tmp_path)
    monkeypatch.setattr("sys.argv", ["inaturalist", "--config", str(config_path)])
    with patch("src.qc_engine.inaturalist.requests.get", side_effect=[
        _mock_response([{"id": 42, "name": "Presbytis femoralis"}]), _mock_response([]),
    ]):
        main()
    output = tmp_path / config["dataset"]["input_path"]
    metadata = json.loads(output.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    raw = json.loads(output.with_suffix(".raw.json").read_text(encoding="utf-8"))
    assert metadata["actual_record_count"] == 0
    assert metadata["observation_ids"] == []
    assert raw["responses"][1]["response"] == {"results": []}
    with output.open(newline="", encoding="utf-8") as handle:
        assert list(csv.DictReader(handle)) == []


def test_failed_download_leaves_existing_snapshot_untouched(tmp_path, monkeypatch):
    config, config_path = _snapshot_config(tmp_path)
    output = tmp_path / config["dataset"]["input_path"]
    output.parent.mkdir(parents=True)
    paths = [output, output.with_suffix(".raw.json"), output.with_suffix(".metadata.json")]
    for path in paths:
        path.write_text("previous snapshot", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["inaturalist", "--config", str(config_path)])
    with patch("src.qc_engine.inaturalist.requests.get", side_effect=[
        _mock_response([{"id": 42, "name": "Presbytis femoralis"}]), requests.HTTPError("unavailable"),
    ]):
        with pytest.raises(requests.HTTPError):
            main()
    assert all(path.read_text(encoding="utf-8") == "previous snapshot" for path in paths)


@pytest.mark.parametrize("count", [0, -1])
def test_invalid_record_count_fails_before_network_or_file_writes(tmp_path, monkeypatch, count):
    config, config_path = _snapshot_config(tmp_path)
    monkeypatch.setattr("sys.argv", ["inaturalist", "--config", str(config_path), "--total-records", str(count)])
    with patch("src.qc_engine.inaturalist.requests.get") as get:
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 2
    get.assert_not_called()
    assert not (tmp_path / config["dataset"]["input_path"]).exists()
