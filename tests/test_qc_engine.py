from pathlib import Path

from src.qc_engine.run import run
from src.project_config import load_config
from src.qc_engine.schema import normalize_observation


ROOT = Path(__file__).parents[1]


def test_reference_oracle_flags_only_out_of_range_coordinates(tmp_path):
    output = tmp_path / "flags.csv"
    flagged = run(ROOT / "data/raw/occurrences_sample.csv", ROOT / "src/oracle_gen/example_oracle.py", output)
    assert flagged == 1
    rows = output.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2
    assert "outside_approximate_range" in rows[1]


def test_reference_oracle_can_include_passes(tmp_path):
    output = tmp_path / "flags.csv"
    run(ROOT / "data/raw/occurrences_sample.csv", ROOT / "src/oracle_gen/example_oracle.py", output, include_passes=True)
    assert len(output.read_text(encoding="utf-8").splitlines()) == 4


def test_inaturalist_response_is_mapped_by_configured_schema():
    config, _ = load_config(ROOT / "config/v0.yaml")
    observation = {
        "id": 123,
        "taxon": {"name": "Presbytis femoralis"},
        "geojson": {"coordinates": [103.8, 1.35]},
        "observed_on": "2025-01-01",
        "quality_grade": "research",
        "user": {"login": "observer"},
    }
    normalized = normalize_observation(observation, config)
    assert normalized["latitude"] == 1.35
    assert normalized["longitude"] == 103.8
    assert normalized["observation_url"].endswith("/123")
