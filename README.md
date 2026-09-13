# FYP: Citizen Science Data Quality

An experimental repository for the Final Year Project Addressing Data Quality Issues in Citizen Science Data.

Prototype V0 explores whether an LLM can generate an executable Python oracle from species knowledge and use it to flag suspicious occurrence records.

## V0 scope

- Species: Raffles' Banded Langur (*Presbytis femoralis*)
- Knowledge source: Wikipedia
- Occurrence platform: iNaturalist
- Oracle generation: an OpenAI-compatible LLM endpoint produces Python
- QC output: a CSV containing records flagged by the generated oracle

V0 intentionally defers intermediate constraint representations, semantic verification, UI, database design, automatic correction, and automatic deletion.

## Setup

    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
    pip install -r requirements.txt

## Quick start without an LLM

    python -m src.qc_engine.run --input data/raw/occurrences_sample.csv
    pytest

The checked-in fixture should produce one flagged record in experiments/runs/v0/flagged_records.csv.

## Fetch iNaturalist observations

    python -m src.qc_engine.inaturalist --taxon "Presbytis femoralis" --output data/raw/occurrences.csv

The downloader resolves the taxon through iNaturalist and stores a normalized CSV. Live observations are ignored by Git by default.

## Generate an oracle with an LLM

    export LLM_API_KEY="your-key"
    # Optional: export LLM_BASE_URL="https://your-endpoint/v1"
    python -m src.oracle_gen.generate --prompt-only
    python -m src.oracle_gen.generate

Inspect generated code before executing it:

    python -m src.qc_engine.run --input data/raw/occurrences.csv --oracle experiments/runs/v0/generated_oracle.py --output experiments/runs/v0/flagged_records.csv

An oracle flags records for human review; it does not prove that a record is erroneous. Do not commit API credentials, large downloads, or unreviewed generated code.
