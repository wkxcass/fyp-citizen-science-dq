# FYP: Citizen Science Data Quality

An experimental repository for the Final Year Project **Addressing Data Quality Issues in Citizen Science Data**.

The project investigates whether species knowledge from public sources can be converted into executable, species-specific data-quality checks for citizen-science occurrence records. The checks are intended to flag records for human review, not to automatically delete or correct them.

## FYP introduction / overview

Citizen-science platforms such as iNaturalist make biodiversity observations widely available, but observations can contain errors that are not caught by general platform or dataset checks. A species-specific check may reveal, for example, that a record for Raffles' Banded Langur appears outside its documented geographic range.

This repository contains the V0 experimental pipeline:

```text
species knowledge + configured dataset schema
    -> prompt assembly
    -> optional LLM-generated Python oracle
    -> oracle execution on occurrence records
    -> flagged-record CSV for human review
```

The current implementation keeps the stages separate so that later experiments can vary the knowledge source, prompt, model, schema, oracle design, or QC policy.

## V0 scope

- Species: Raffles' Banded Langur (*Presbytis femoralis*)
- Knowledge source: Wikipedia
- Occurrence platform: iNaturalist
- Dataset representation: a normalized schema defined in `config/v0.yaml`
- Oracle generation: an OpenAI-compatible LLM endpoint produces Python
- QC output: a CSV containing records flagged by the oracle

V0 deliberately keeps the prototype small. It currently defers intermediate constraint representations, semantic verification, user interfaces, database design, automatic correction, and automatic deletion. A flag means that a record deserves review; it is not proof that the record is erroneous.

## Setup

Run these commands from the repository root.

### Linux / Ubuntu

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks virtual-environment activation, allow it for the current PowerShell process only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Open `.env` and replace the placeholder with your Groq API key:

```env
LLM_API_KEY=your_groq_api_key_here
```

The repository loads this file automatically when a command loads `config/v0.yaml`. `.env` is ignored by Git and must never be committed.

`config/v0.yaml` is the canonical V0 experiment configuration. It defines the species, source, iNaturalist endpoint, normalized schema, model, prompt path, input/output paths, and generated-oracle path. Command-line arguments are available as explicit per-run overrides.

## Guide for reference smoke test

This test exercises the QC engine without downloading data or calling an LLM. It uses the checked-in fixture `data/raw/occurrences_sample.csv` and the transparent reference oracle `src/oracle_gen/example_oracle.py`.

### Linux / Ubuntu

```bash
python -m src.qc_engine.run \
  --config config/v0.yaml \
  --input data/raw/occurrences_sample.csv \
  --oracle src/oracle_gen/example_oracle.py
pytest
```

### Windows PowerShell

```powershell
python -m src.qc_engine.run `
  --config config/v0.yaml `
  --input data/raw/occurrences_sample.csv `
  --oracle src/oracle_gen/example_oracle.py
pytest
```

The command writes flagged records to the configured QC output path:

```text
experiments/runs/v0/flagged_records.csv
```

The fixture is expected to produce one flagged record. The reference oracle is only a deterministic smoke-test oracle; it is not the LLM-generated artifact.

## Guide to trigger actual pipeline

This path fetches live iNaturalist observations, asks the configured LLM to generate an oracle, and runs that oracle against the fetched data.

### 1. Fetch iNaturalist data

The downloader resolves the configured taxon and writes normalized observations to the configured input path, `data/raw/occurrences.csv`.

Linux / Ubuntu:

```bash
python -m src.qc_engine.inaturalist --config config/v0.yaml
```

Windows PowerShell:

```powershell
python -m src.qc_engine.inaturalist --config config/v0.yaml
```

### 2. Generate an oracle using the configured LLM

Before making the API call, you can inspect the assembled prompt:

Linux / Ubuntu:

```bash
python -m src.oracle_gen.generate --config config/v0.yaml --prompt-only
```

Windows PowerShell:

```powershell
python -m src.oracle_gen.generate --config config/v0.yaml --prompt-only
```

Generate the Python oracle:

Linux / Ubuntu:

```bash
python -m src.oracle_gen.generate --config config/v0.yaml
```

Windows PowerShell:

```powershell
python -m src.oracle_gen.generate --config config/v0.yaml
```

The generated file is written to `experiments/runs/v0/generated_oracle.py`. Inspect it before execution: it should define `check_record(record)` and should not contain Markdown code-fence markers.

### 3. Run QC on the fetched data

Linux / Ubuntu:

```bash
python -m src.qc_engine.run --config config/v0.yaml
```

Windows PowerShell:

```powershell
python -m src.qc_engine.run --config config/v0.yaml
```

The QC runner dynamically loads the configured oracle, applies `check_record(record)` to each normalized occurrence, and writes flagged records to `experiments/runs/v0/flagged_records.csv`.

## Configuration and development notes

- Keep prompts versioned under `prompts/`; do not bury prompt text in Python code.
- Keep small, intentional fixtures under `data/raw/`; live downloads and generated outputs are ignored by Git.
- Review generated Python before running it. V0 generates executable code, so the generated artifact is an experimental input rather than trusted production code.
- Do not commit `.env`, API credentials, large downloads, or unreviewed generated artifacts.

See `docs/architecture.md` for the component relationships and `docs/decisions.md` for recorded design decisions.
