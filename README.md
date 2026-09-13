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
    cp .env.example .env

Open `.env` and replace the placeholder with your Groq API key. The `.env` file is ignored by Git and must never be committed.

## Quick start without an LLM

    python -m src.qc_engine.run --config config/v0.yaml --input data/raw/occurrences_sample.csv --oracle src/oracle_gen/example_oracle.py
    pytest

The checked-in fixture should produce one flagged record in experiments/runs/v0/flagged_records.csv.

## Fetch iNaturalist observations

    python -m src.qc_engine.inaturalist --config config/v0.yaml

The downloader resolves the taxon through iNaturalist and stores a normalized CSV. Live observations are ignored by Git by default.

## Generate an oracle with an LLM

    python -m src.oracle_gen.generate --config config/v0.yaml --prompt-only
    python -m src.oracle_gen.generate --config config/v0.yaml

Inspect generated code before executing it:

    python -m src.qc_engine.run --config config/v0.yaml

An oracle flags records for human review; it does not prove that a record is erroneous. Do not commit API credentials, large downloads, or unreviewed generated code.
