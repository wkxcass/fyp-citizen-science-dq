# FYP: Citizen Science Data Quality

An experimental repository for the Final Year Project **Addressing Data Quality Issues in Citizen Science Data**.

Prototype V0 will explore whether an LLM can generate an executable Python oracle from species knowledge and use it to flag suspicious occurrence records.

## V0 scope

- Species: Raffles' Banded Langur (*Presbytis femoralis*)
- Knowledge source: Wikipedia
- Occurrence data: GBIF or an iNaturalist-derived dataset; the exact source will be fixed before execution
- Oracle generation: an LLM produces Python
- QC output: a CSV containing records flagged by the generated oracle

Intermediate constraint representations, hard/soft constraint modelling, semantic verification, UI, and database design are intentionally deferred until V0 provides evidence that they are useful.

## Repository layout

- `src/oracle_gen/`: knowledge source to executable oracle
- `src/qc_engine/`: run an oracle against occurrence records
- `prompts/`: versioned prompt templates
- `config/`: reproducible experiment settings
- `data/raw/`: small, redistributable fixtures only
- `data/processed/`: derived local outputs
- `experiments/`: experiment records and run outputs
- `docs/`: architecture and decision records
- `tests/`: automated tests

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Running V0

The V0 command will be documented here once the first implementation is added. This repository-initialization step contains no prototype implementation yet.

## Reproducibility

Record meaningful changes in `docs/decisions.md` and each experiment in `experiments/log.csv`. Generated data, API credentials, and large or licensed downloads must not be committed.
