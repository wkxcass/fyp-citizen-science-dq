# Preliminary V0 Architecture

V0 is intentionally a small end-to-end experimental pipeline:

1. A species knowledge source is supplied to an LLM together with the selected occurrence-data schema.
2. The LLM generates an executable Python oracle.
3. The QC engine loads occurrence records for *Presbytis femoralis*.
4. The engine executes the oracle against applicable records.
5. The system writes suspicious-record results to CSV.

The generated oracle is an experimental artefact and must be inspected before its output is treated as evidence. V0 flags records for review; it does not automatically correct or delete data.

## Current boundaries

V0 starts with ecological and spatial knowledge, while allowing the model to identify adjacent potentially testable concepts. Unsupported concepts are recorded for later analysis rather than implemented in advance.

The following are deliberately not fixed yet: the final dataset platform (GBIF versus iNaturalist-derived data), intermediate constraint representation, hard/soft constraint treatment, semantic verification, UI, and database design.
