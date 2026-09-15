# Decision Log

## v0

- **D001 — Minimal executable-oracle V0**
  - Status: Settled
  - Decision: One species, Wikipedia, iNaturalist, one normalized CSV schema, one LLM-generated Python oracle, and CSV flags.
  - Rationale: Establish a complete experimental path before extensions.

- **D002 — Defer architectural extensions**
  - Status: Settled
  - Decision: Defer intermediate constraints, hard-versus-soft modelling, semantic verification, UI, database design, and automatic correction.
  - Rationale: Use V0 observations to determine which extensions are justified.

- **D003 — Normalize the platform boundary**
  - Status: Settled
  - Decision: Convert iNaturalist observations into a small stable CSV schema before oracle execution.
  - Rationale: Keeps the oracle/QC runner focused and makes later data-source comparisons possible.

- **D004 — Use a reference oracle for smoke tests**
  - Status: Settled
  - Decision: Include a transparent reference oracle and small fixture so QC mechanics can be tested without an LLM or live API.
  - Rationale: Separates infrastructure failures from model-generation failures.

- **D005 — Load secrets from a local dotenv file**
  - Status: Settled
  - Decision: Store the local LLM credential in `.env`, documented by tracked `.env.example`, and load it through the shared configuration helper.
  - Rationale: Avoid repeated shell exports without placing credentials in Git.

- **D006 — Fetch by total_records, paginating internally**
  - Status: Settled
  - Decision: Replace the `per_page`-based iNaturalist fetch (which silently capped at a single page, ≤100 records) with a `total_records` config value. `fetch_observations` now pages through the API internally until that cap is reached or results run out, using `per_page` only as an internal batch size bounded by iNaturalist's 200-per-request ceiling.
  - Rationale: `per_page` conflated a pagination implementation detail with the actual experimental variable researchers care about — how many records to pull. Fixing this also resolved a real bug: V0 was silently working with far fewer observations than intended.

## Open variables for later experiments

Prompt wording and source-text amount; model and decoding settings; direct Python versus intermediate representation; supported fields and constraint families; missing-value and probabilistic-statement treatment; oracle review; platform adapters; and evaluation criteria.