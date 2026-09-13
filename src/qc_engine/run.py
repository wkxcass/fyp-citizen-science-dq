"""Run an oracle against an occurrence CSV and write suspicious records."""

from __future__ import annotations

import argparse
import csv
import importlib.util
from pathlib import Path
from typing import Any

from src.project_config import load_config, resolve_path


def load_oracle(path: str | Path):
    spec = importlib.util.spec_from_file_location("generated_oracle", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load oracle from {path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "check_record"):
        raise RuntimeError("Oracle must define check_record(record) -> list[dict].")
    return module.check_record


def run(input_path: str | Path, oracle_path: str | Path, output_path: str | Path, include_passes: bool = False) -> int:
    check_record = load_oracle(oracle_path)
    with Path(input_path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        records = list(reader)
        input_fields = reader.fieldnames or []
    fields = [*input_fields, "flag_code", "reason"]
    flagged = 0
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            flags: list[dict[str, Any]] = check_record(record)
            if flags:
                flagged += 1
                for flag in flags:
                    writer.writerow({**record, **flag})
            elif include_passes:
                writer.writerow({**record, "flag_code": "", "reason": ""})
    return flagged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/v0.yaml")
    parser.add_argument("--input")
    parser.add_argument("--oracle")
    parser.add_argument("--output")
    parser.add_argument("--include-passes", action="store_true")
    args = parser.parse_args()
    config, repo_root = load_config(args.config)
    input_path = Path(args.input) if args.input else resolve_path(repo_root, config["dataset"]["input_path"])
    oracle_path = Path(args.oracle) if args.oracle else resolve_path(repo_root, config["qc"]["oracle_path"])
    output_path = Path(args.output) if args.output else resolve_path(repo_root, config["qc"]["output_path"])
    print(f"Flagged {run(input_path, oracle_path, output_path, args.include_passes)} record(s). Output: {output_path}")


if __name__ == "__main__":
    main()
