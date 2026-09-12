# Decision Log

## D001 — Minimal executable-oracle V0

- Status: Tentative
- Decision: One species, Wikipedia, iNaturalist, one normalized CSV schema, one LLM-generated Python oracle, and CSV flags.
- Rationale: Establish a complete experimental path before extensions.

## D002 — Defer architectural extensions

- Status: Tentative
- Decision: Defer intermediate constraints, hard-versus-soft modelling, semantic verification, UI, database design, and automatic correction.
- Rationale: Use V0 observations to determine which extensions are justified.

## D003 — Normalize the platform boundary

- Status: Tentative
- Decision: Convert iNaturalist observations into a small stable CSV schema before oracle execution.
- Rationale: Keeps the oracle/QC runner focused and makes later data-source comparisons possible.

## D004 — Use a reference oracle for smoke tests

- Status: Tentative
- Decision: Include a transparent reference oracle and small fixture so QC mechanics can be tested without an LLM or live API.
- Rationale: Separates infrastructure failures from model-generation failures.

## Open variables for later experiments

Prompt wording and source-text amount; model and decoding settings; direct Python versus intermediate representation; supported fields and constraint families; missing-value and probabilistic-statement treatment; oracle review; platform adapters; and evaluation criteria.
