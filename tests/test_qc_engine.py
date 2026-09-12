from pathlib import Path

from src.qc_engine.run import run


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
