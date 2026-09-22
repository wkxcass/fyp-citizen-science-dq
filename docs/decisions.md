# Decision Log

## v0

- **D001 — Minimal executable-oracle v0**
  - Status: Resolved
  - Decision: One species, Wikipedia, iNaturalist, one normalized CSV schema, one LLM-generated Python oracle, and CSV flags.
  - Rationale: Establish a complete experimental path before extensions.

- **D002 — Defer architectural extensions**
  - Status: Resolved
  - Decision: Defer intermediate constraints, hard-versus-soft modelling, semantic verification, UI, database design, and automatic correction.
  - Rationale: Use v0 observations to determine which extensions are justified.

- **D003 — Normalize the platform boundary**
  - Status: Resolved
  - Decision: Convert iNaturalist observations into a small stable CSV schema before oracle execution.
  - Rationale: Keeps the oracle/QC runner focused and makes later data-source comparisons possible.

- **D004 — Use a reference oracle for smoke tests**
  - Status: Resolved
  - Decision: Include a transparent reference oracle and small fixture so QC mechanics can be tested without an LLM or live API.
  - Rationale: Separates infrastructure failures from model-generation failures.

- **D005 — Load secrets from a local dotenv file**
  - Status: Resolved
  - Decision: Store the local LLM credential in `.env`, documented by tracked `.env.example`, and load it through the shared configuration helper.
  - Rationale: Avoid repeated shell exports without placing credentials in Git.

- **D006 — Fetch by total_records, paginating internally**
  - Status: Resolved
  - Decision: Replace the `per_page`-based iNaturalist fetch (which silently capped at a single page, ≤100 records) with a `total_records` config value. `fetch_observations` now pages through the API internally until that cap is reached or results run out, using `per_page` only as an internal batch size bounded by iNaturalist's 200-per-request ceiling.
  - Rationale: `per_page` conflated a pagination implementation detail with the actual experimental variable researchers care about — how many records to pull. Fixing this also resolved a real bug: v0 was silently working with far fewer observations than intended.

## v0 → v0.1

- **D007 — Verbosity of "untestable adjacent concepts" commentary vs. token budget**
  - Status: Tentative
  - Decision: TBD — keep, shorten, or relocate (e.g. structured metadata instead of inline code comments) the prompt instruction asking the LLM to comment on constraints it couldn't implement.
  - Rationale: Valuable design signal but consumes generation-token budget and may contribute to output (code) truncation. Likely resolved for free once D008/D009/D010 land, since this information becomes a structured field in the constraint JSON rather than a prose comment.

- **D008 — Two-stage constraint extraction (knowledge → constraints → oracle)**
  - Status: Tentative
  - Decision: Split oracle generation into (1) knowledge → structured constraints, schema-blind, and (2) constraints + schema → Python oracle.
  - Rationale: Directly targets schema-first contamination by removing the schema from the LLM's context during constraint extraction.
  - Open question: exact intermediate representation — see D009.

- **D009 — Intermediate constraint representation format**
  - Status: Tentative
  - Decision: Represent extracted constraints as JSON (concept, target field(s), condition, category, testability tier, hard/soft) rather than XPath or a custom DSL.
  - Rationale: Cheapest to generate, validate, and diff across experiment runs. Also resolves an open design question about whether a more expressive interface or domain-specific language (e.g. XPath, a bespoke constraint language) is warranted at this stage; a lightweight JSON representation is sufficient for v0.1's needs and avoids that additional complexity until proven necessary.

- **D010 — Classification scheme for constraint/statement types**
  - Status: Tentative
  - Decision: Derive category + testability-tier labels empirically from sampled knowledge-source text rather than committing to {spatial/biological/ecological/phenological} a priori.
  - Rationale: A small sample of species descriptions was reviewed to establish which statement types are actually operationalizable against the current schema (informing what "testable" means in practice) and to surface a first-pass classification scheme grounded in real examples rather than an assumed taxonomy. Formal multi-rater agreement (e.g. Cohen's Kappa) is not pursued given this is solo FYP work; a single analysis pass, revisited as needed, is treated as sufficient.

- **D011 — Schema/runtime type-contract mismatch**
  - Status: Resolved
  - Decision: The QC engine coerces CSV field values to their configured schema `type` via `normalize_record()`/`coerce_value()` before calling `check_record`; empty string is treated as missing (`None`), and unparseable-but-present values are left unchanged rather than collapsed into `None`, since malformed and missing are distinct conditions. The runtime type contract is also documented explicitly in `prompts/oracle_v0.1.md`.
  - Rationale: `config/v0.yaml` declares `latitude`/`longitude` as `type: number`, but `qc_engine/run.py` reads occurrence CSVs via `csv.DictReader`, so `check_record` always receives raw strings. Observed in v0/1 (isinstance-only check silently never fires) and v0/2 (empty-string cast to float raises, misclassified as "invalid" instead of "missing"). A QC-engine/prompt contract gap, not primarily an LLM-capability issue.

- **D012 — Taxon-name check: redundant defensive validation or dead weight?**
  - Status: Tentative
  - Decision: TBD — decide whether generated oracles should validate `taxon_name` themselves (defensive, for mixed-species/manually-edited datasets) or omit it as dead code (v0's fetch step already constrains downloads to a single `taxon_id`, so the field is tautologically constant today).
  - Rationale: Recurred in multiple v0 oracles. Also connects to an open extensibility question: v0 is scoped to a single species with taxon filtering handled upstream by the fetch step, but a future multi-species version would need to decide whether that filtering should remain the QC engine's responsibility, be pushed into each generated oracle, or both — this decision is a small first instance of that larger design question.

- **D013 — Mutation-testing feedback loop**
  - Status: Tentative
  - Decision: Build a synthetic-corruption harness (coordinate shifts, blanked fields, taxon swaps) to measure oracle detection rate, as a keep/ditch evaluation signal.
  - Rationale: Provides a lightweight way to gauge whether a generated oracle (or an architectural change such as D008's two-stage split) actually improves detection of suspicious records, without requiring an extensive hand-labelled ground-truth dataset up front.

- **D014 — Unattributed run-to-run variance in schema-first-contamination rate**
  - Status: Tentative
  - Decision: TBD — not pursued further for now.
  - Rationale: Candidate factors, none investigated: (a) provider-side nondeterminism on Groq's serving stack for openai/gpt-oss-20b — MoE expert routing and/or reasoning-effort behavior potentially sensitive to batch composition/session context, outside client-side control; (b) uncontrolled temporal/session clustering — the original v0 runs were collected ad hoc across the early dev period, while the v0.1/4 ablation was interleaved within a single session, and this alone could account for the gap between the two measured baseline rates independent of any prompt or engine change.

## Open variables for later experiments

- Prompt wording and source-text amount
- Missing-value and probabilistic-statement treatment
- Model and decoding settings
- Oracle review and evaluation criteria
- Platform adapters
- etc.