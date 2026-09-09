# Decision Log

Use this file to record decisions made from prototype observations. Keep superseded decisions rather than deleting them.

## D001 — Minimal executable-oracle V0

- **Status:** Tentative
- **Decision:** Start with one species, one knowledge source, one occurrence-data schema, one LLM-generated Python oracle, and CSV flags.
- **Rationale:** Establish a complete experimental path before adding architectural extensions.
- **Scope:** Raffles' Banded Langur (*Presbytis femoralis*), Wikipedia, and GBIF/iNaturalist-derived occurrence records.

## D002 — Defer architectural extensions

- **Status:** Tentative
- **Decision:** Defer intermediate constraints, hard-versus-soft modelling, semantic verification, UI, and database design.
- **Rationale:** Use V0 observations to determine which extensions are justified.

## D003 — Keep data-source choice open briefly

- **Status:** Open
- **Question:** Should V0 use GBIF directly or an iNaturalist-derived dataset?
- **Next evidence:** Compare schema clarity, record availability, and licensing/redistribution constraints for the selected species.
