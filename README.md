# 🎓 FYP: Citizen Science Data Quality

An experimental repository for the Final Year Project **Addressing Data Quality Issues in Citizen Science Data**.

The project investigates whether species knowledge from public sources can be converted into executable, species-specific data-quality checks for citizen-science occurrence records. The checks are intended to flag records for human review, not to automatically delete or correct them.

## 🌱 FYP Introduction / Overview

Citizen-science platforms such as iNaturalist make biodiversity observations widely available, but observations can contain errors that are not caught by general platform or dataset checks. A species-specific check may reveal, for example, that a record for Raffles' Banded Langur appears outside its documented geographic range.

This repository contains the v1 experimental pipeline:

```text
species knowledge + configured dataset schema
    -> prompt assembly
    -> optional LLM-generated Python oracle
    -> oracle execution on occurrence records
    -> flagged-record CSV for human review
```

The current implementation keeps the stages separate so that later experiments can vary the knowledge source, prompt, model, schema, oracle design, or QC policy.

## 💡 v1 Scope

- Species: Raffles' Banded Langur (*Presbytis femoralis*), Sunda Pangolin (*Manis javanica*), Oriental Pied Hornbill (*Anthracoceros albirostris*), and Straw-headed Bulbul (*Pycnonotus zeylanicus*)
- Knowledge source: Wikipedia article text
- Occurrence platform: iNaturalist
- Dataset representation: the existing normalized schema in `config/v1_langur.yaml`, `config/v1_pangolin.yaml`, `config/v1_hornbill.yaml`, and `config/v1_bulbul.yaml`
- Oracle generation: `prompts/v1.md` scopes generation to source-supported spatial/geographical review checks; the pilot uses `openai/gpt-oss-20b` via Groq to produce Python
- QC output: a CSV containing records flagged by the oracle

v1 focuses on documented distribution and locality expectations. Habitat, elevation, seasonal and morphological checks are outside this iteration. Intermediate constraint representations, semantic verification, user interfaces, database design, automatic correction, and automatic deletion remain deferred. A flag is a candidate for review, not proof that the record is erroneous.

## 💻 Setup

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

The repository loads this file automatically when a command loads a config under `config/`. `.env` is ignored by Git and must never be committed.

Each `config/v1_<species>.yaml` defines the species, source, iNaturalist endpoint, normalized schema, model, prompt path, input/output paths, and generated-oracle path. Command-line arguments are available as explicit per-run overrides.

The examples below use the langur config; substitute the other species' v1 configs as needed. For repeated evaluation, reuse the frozen occurrence files. Rerunning a fetch at the same output path replaces its snapshot files.

## ☁ Guide for Reference Smoke Test

This test exercises the QC engine without downloading data or calling an LLM. It uses the checked-in fixture `data/raw/occurrences_sample.csv` and the transparent reference oracle `src/oracle_gen/example_oracle.py`.

### Linux / Ubuntu

```bash
python -m src.qc_engine.run \
  --config config/v1_langur.yaml \
  --input data/raw/occurrences_sample.csv \
  --oracle src/oracle_gen/example_oracle.py
pytest
```

### Windows PowerShell

```powershell
python -m src.qc_engine.run `
  --config config/v1_langur.yaml `
  --input data/raw/occurrences_sample.csv `
  --oracle src/oracle_gen/example_oracle.py
pytest
```

The command writes flagged records to the configured QC output path:

```text
experiments/runs/v1/flagged_records_langur.csv
```

The fixture is expected to produce one flagged record. The reference oracle is only a deterministic smoke-test oracle; it is not the LLM-generated artifact.

## ⚙ Guide to Trigger Actual Pipeline

This path fetches live iNaturalist observations, asks the configured LLM to generate an oracle, and runs that oracle against the fetched data.

### 1. Fetch iNaturalist data

The downloader resolves the configured taxon and writes normalized observations to the configured input path, `data/raw/v1/occurrences_langur.csv`. It also saves the complete public JSON responses and retrieval metadata alongside that CSV. No additional configuration entries are needed.

Linux / Ubuntu:

```bash
python -m src.qc_engine.inaturalist --config config/v1_langur.yaml
```

Windows PowerShell:

```powershell
python -m src.qc_engine.inaturalist --config config/v1_langur.yaml
```

For the langur input path ending in `occurrences_langur.csv`, each fetch writes:

| File | Purpose |
|---|---|
| `occurrences_langur.csv` | The existing normalized input for the QC runner; its columns are unchanged. |
| `occurrences_langur.raw.json` | A `responses` list containing the taxon lookup and every fetched observation page. Each entry stores the request URL, parameters, UTC retrieval time and complete decoded JSON response. |
| `occurrences_langur.metadata.json` | Start/end retrieval times in UTC, requested species, resolved taxon ID/name, requested/actual counts, exact request settings, selected observation IDs, schema mapping and companion filenames. |

The JSON files use the same directory and filename stem as the CSV, including when `--output` overrides its location. The fetcher uses `dataset.api_base_url` and preserves the current ordering (`created_at`, descending). It stops at the requested count or when observations run out. Page size stays fixed across requests so page offsets remain consistent; the raw final page can contain more observations than the selected CSV. The metadata's `observation_ids` identify the records actually selected for the CSV.

The raw responses retain public fields omitted from the normalized schema, such as obscuration, positional accuracy and captive status when supplied by iNaturalist. For later review, match a CSV `observation_id` to an observation's `id` under `responses[*].response.results`. The first response is the taxon lookup; observation pages follow. These files preserve the public response and do not recover hidden coordinates.

### 2. Generate an oracle using the configured LLM

Wikipedia retrieval uses the MediaWiki API to request article plain text. It preserves section headings and applies no character or sentence limit. This is article prose, not a complete representation of infoboxes, range maps or other non-prose content. Missing pages, API errors and empty extracts stop generation instead of silently supplying empty knowledge.

Before making the API call, you can inspect the assembled prompt:

Linux / Ubuntu:

```bash
python -m src.oracle_gen.generate --config config/v1_langur.yaml --prompt-only
```

Windows PowerShell:

```powershell
python -m src.oracle_gen.generate --config config/v1_langur.yaml --prompt-only
```

Generate the Python oracle:

Linux / Ubuntu:

```bash
python -m src.oracle_gen.generate --config config/v1_langur.yaml
```

Windows PowerShell:

```powershell
python -m src.oracle_gen.generate --config config/v1_langur.yaml
```

The generated file is written to `experiments/runs/v1/generated_oracle_langur.py`. Inspect it before execution: it should define `check_record(record)` and should not contain Markdown code-fence markers.

Both prompt-only and LLM-generation commands save the exact input text as `<output-stem>.knowledge.txt` and the assembled prompt as `<output-stem>.prompt.txt`, beside the configured or overridden oracle output. Prompt-only does not call the LLM or write an oracle. These input files are saved before any LLM call, including attempts whose generation later fails.

### 3. Run QC on the fetched data

Linux / Ubuntu:

```bash
python -m src.qc_engine.run --config config/v1_langur.yaml
```

Windows PowerShell:

```powershell
python -m src.qc_engine.run --config config/v1_langur.yaml
```

The QC runner dynamically loads the configured oracle, applies `check_record(record)` to each normalized occurrence, and writes flagged records to `experiments/runs/v1/flagged_records_langur.csv`.

## ❗ Configuration & Development Notes

- Keep prompts versioned under `prompts/`; do not bury prompt text in Python code.
- Keep small, intentional fixtures under `data/raw/`; live downloads and generated outputs are ignored by Git.
- Review generated Python before running it. The prototype generates executable code, so the generated artifact is an experimental input rather than trusted production code.
- Do not commit `.env`, API credentials, large downloads, or unreviewed generated artifacts.

See `docs/architecture.md` for the component relationships and `docs/decisions.md` for recorded decisions.

## 🔍 Motivation Study

A small, separate study of what species knowledge sources say versus what citizen-science platforms actually record. It supports the comparison table and `experiments/motivation_study/log.csv`.

`scripts/platform_field_check.py` pulls up to 100 records per species from the iNaturalist API and from the GBIF copies of iNaturalist, Observation.org and eBird. It then counts how often each field is filled. No API keys or logins are needed.

### Linux / Ubuntu

```bash
python scripts/platform_field_check.py --out experiments/motivation_study/snapshot_YYYY-MM-DD
```

### Windows PowerShell

```powershell
python scripts/platform_field_check.py --out experiments/motivation_study/snapshot_YYYY-MM-DD
```

- Outputs are CSV summaries (`*_fields.csv`, `record_counts.csv`, `gbif_issue_flags.csv`), a `run_log.txt` and a zip of everything.
- The reference snapshot is `snapshot_2026-10-03`. Counts drift as platforms grow, so re-runs will differ slightly.
- `sample_records.json` and the zip are git-ignored because they hold individual records.

## 🏁 Preliminary Checkpoint — 23 October 2026

The pilot uses 100 frozen iNaturalist records per species, fetched on 21 October, and three generated oracles per species. All 12 generations succeeded. Unique flagged observation counts were:

| Species | Run 1 | Run 2 | Run 3 |
|---|---:|---:|---:|
| Langur | 0 | 0 | 0 |
| Pangolin | 7 | 7 | 7 |
| Hornbill | 92 | 91 | 53 |
| Bulbul | 0 | 0 | 0 |

RQ1 review covered all 13 geographic conditions: none added quality-grade, observer or taxon-name validation, but all introduced numerical boundaries absent from the supplied text. Some translations contradicted the source, and some qualifiers were lost. This does not establish reduced contamination against a controlled baseline.

RQ3 review of six deliberately selected flagged cases found five legitimate exceptions or misleading flags and one unresolved case; no new biological occurrence discrepancy was established among those cases. Captive status, specimen descriptions and obscured coordinates affected interpretation. These are qualitative findings, not accuracy estimates; zero flags do not establish absence of suspicious records. Systematic RQ2 correctness evaluation is deferred, with mutation-testing concepts under consideration for future evaluation. See `experiments/runs/log.csv` and `docs/decisions.md`.

## ℹ️ AI Tool Disclosure

AI-assisted tools, including GPT-6.1 and Claude Sonnet 5.5, were utilized during the preparation and development of this repository. Specifically, these models assisted with:
- Documentation Synthesis: Generating and structuring documentation content directly from manually maintained FYP notes and logs.
- Code Implementation: Translating high-level architecture, design frameworks and development plans presented by the author into functional code.
