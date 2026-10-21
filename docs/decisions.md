# Decision Log

- **D001 — Minimal executable-oracle v0**
  - Status: Resolved (v0) ✅
  - Decision: One species, Wikipedia, iNaturalist, one normalized CSV schema, one LLM-generated Python oracle, and CSV flags.
  - Rationale: Establish a complete experimental path before extensions.

- **D002 — Defer architectural extensions**
  - Status: Resolved (v0) ✅
  - Decision: Defer intermediate constraints, hard-versus-soft modelling, semantic verification, UI, database design, and automatic correction.
  - Rationale: Use v0 observations to determine which extensions are justified.

- **D003 — Normalization of platform boundary**
  - Status: Provisional ⚠️
  - Decision: Continue using the existing mapping from iNaturalist observations to the configured CSV fields. Defer redesign or generalisation of this interface until a concrete experimental requirement justifies it.
  - Rationale: The existing mapping provides a small, predictable interface for oracle generation, execution and inspection. Normalization is an implementation convenience rather than a requirement of the research approach. Its suitability for additional platforms or richer checks has not been established.

- **D004 — Use a reference oracle for smoke tests**
  - Status: Resolved (v0) ✅
  - Decision: Include a transparent reference oracle and small fixture so QC mechanics can be tested without an LLM or live API.
  - Rationale: Separates infrastructure failures from model-generation failures.

- **D005 — Load secrets from a local dotenv file**
  - Status: Resolved (v0) ✅
  - Decision: Store the local LLM credential in `.env`, documented by tracked `.env.example`, and load it through the shared configuration helper.
  - Rationale: Avoid repeated shell exports without placing credentials in Git.

- **D006 — Fetch by total_records, paginating internally**
  - Status: Resolved (v0) ✅
  - Decision: Replace the `per_page`-based iNaturalist fetch (which silently capped at a single page, ≤100 records) with a `total_records` config value. `fetch_observations` now pages through the API internally until that cap is reached or results run out, using `per_page` only as an internal batch size bounded by iNaturalist's 200-per-request ceiling.
  - Rationale: `per_page` conflated a pagination implementation detail with the actual experimental variable researchers care about — how many records to pull. Fixing this also resolved a real bug: v0 was silently working with far fewer observations than intended.

- **D007 — Verbosity of "untestable adjacent concepts" commentary vs. token budget**
  - Status: Tentative ⛔
  - Decision: TBD — keep, shorten, or relocate (e.g. structured metadata instead of inline code comments) the prompt instruction asking the LLM to comment on constraints it couldn't implement.
  - Rationale: Valuable design signal but consumes generation-token budget and may contribute to output (code) truncation.

- **D008 — Empirical constraint classification to guide generation**
  - Status: Provisional ⚠️
  - Decision: Classify sampled species statements by their meaning and checkability independently of the current dataset schema, then assess whether the required evidence is available directly, requires external data, or is unavailable. Use this analysis to guide v1 generation toward source-supported spatial/geographical checks on iNaturalist records and to address schema-first contamination. A field's presence alone must not justify a species-derived rule; generated conditions should preserve the source's scope, qualifiers and uncertainty.
  - Rationale: The empirical source/platform review identified geographic information as the clearest immediate overlap between species knowledge and accessible occurrence evidence. Classification therefore informs prototype scope, prompting and evaluation. Whether this guidance reduces contamination remains to be evaluated. The scheme is based on a single-analyst review appropriate to the solo FYP and may be revised as further examples arise.

- **D009 — Schema/runtime type-contract mismatch**
  - Status: Resolved (v0.1) ✅
  - Decision: The QC engine coerces CSV field values to their configured schema `type` via `normalize_record()`/`coerce_value()` before calling `check_record`; empty string is treated as missing (`None`), and unparseable-but-present values are left unchanged rather than collapsed into `None`, since malformed and missing are distinct conditions. The runtime type contract is also documented explicitly in `prompts/oracle_v0.1.md`.
  - Rationale: `config/v0.yaml` declares `latitude`/`longitude` as `type: number`, but `qc_engine/run.py` reads occurrence CSVs via `csv.DictReader`, so `check_record` always receives raw strings. Observed in v0/1 (isinstance-only check silently never fires) and v0/2 (empty-string cast to float raises, misclassified as "invalid" instead of "missing"). A QC-engine/prompt contract gap, not primarily an LLM-capability issue.

- **D010 — Taxon-name check: redundant defensive validation or dead weight?**
  - Status: Tentative ⛔
  - Decision: TBD — decide whether generated oracles should validate `taxon_name` themselves (defensive, for mixed-species/manually-edited datasets) or omit it as dead code (v0's fetch step already constrains downloads to a single `taxon_id`, so the field is tautologically constant today).
  - Rationale: Recurred in multiple v0 oracles. Also connects to an open extensibility question: v0 is scoped to a single species with taxon filtering handled upstream by the fetch step, but a future multi-species version would need to decide whether that filtering should remain the QC engine's responsibility, be pushed into each generated oracle, or both — this decision is a small first instance of that larger design question.

- **D011 — Unattributed run-to-run variance in schema-first-contamination rate**
  - Status: Tentative ⛔
  - Decision: TBD — not pursued further for now.
  - Rationale: Candidate factors, none investigated: (a) provider-side nondeterminism on Groq's serving stack for openai/gpt-oss-20b — MoE expert routing and/or reasoning-effort behavior potentially sensitive to batch composition/session context, outside client-side control; (b) uncontrolled temporal/session clustering — the original v0 runs were collected ad hoc across the early dev period, while the v0.1/4 ablation was interleaved within a single session, and this alone could account for the gap between the two measured baseline rates independent of any prompt or engine change.

- **D012 — Mutation-testing feedback loop**
  - Status: Tentative ⛔
  - Decision: Build a synthetic-corruption harness (coordinate shifts, blanked fields, taxon swaps) to measure oracle detection rate, as a keep/ditch evaluation signal.
  - Rationale: Provides a lightweight way to gauge whether a generated oracle actually improves detection of suspicious records, without requiring an extensive hand-labelled ground-truth dataset up front.

## Open variables for later experiments

- Prompt wording and source-text amount
- Missing-value and probabilistic-statement treatment
- Model (e.g., using NUS SOC LMMaaS) and decoding settings
- Executable-rule representation format
- Two-stage constraint extraction and verification layer(s)
- Extended oracle review and evaluation criteria
- UI and platform adapters
- Adaptations of related work
- etc.