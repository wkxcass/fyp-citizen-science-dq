# Prototype v1 Architecture

The pipeline:

1. Fetch Wikipedia article plain text for the configured species.
2. Combine that text with the normalized iNaturalist CSV schema and the spatial-generation instructions in `prompts/v1.md`.
3. Save the knowledge text and assembled prompt beside the oracle output. Optionally call an OpenAI-compatible chat-completions endpoint, validate Python syntax and the `check_record` entry point, and save the generated module.
4. Resolve the species through iNaturalist, fetch observations, and normalize them into CSV. Save the complete public responses in a companion `.raw.json` and retrieval metadata in `.metadata.json`.
5. Normalize each CSV row to the schema's declared field types (empty string → `None`; unparseable-but-present values left unchanged), then load an oracle, call `check_record(record)` for each row, and write one output row per flag.

The checked-in reference oracle exercises the QC mechanics without an LLM or live API. It is a test harness, not the research result.

The four `config/v1_<species>.yaml` files share the same occurrence interface and oracle contract. The pilot freezes 100 observations and one knowledge text per species, reusing them across three generation attempts. Raw-response metadata supports later review of captive status, obscuration and location uncertainty; it is not passed to generated oracles through the current CSV schema.

## Oracle contract

    def check_record(record: dict) -> list[dict[str, str]]:
        ...

An empty list means no applicable review flag; it can also represent a skipped assessment (the v1 prompt requires missing or unusable coordinates to be skipped rather than flagged as geographic inconsistencies) and does not validate the record. A returned dictionary contains only a stable flag_code and human-readable reason. The prototype flags for human review; it does not automatically clean, correct, or delete records.

## Deliberate boundaries

Only a normalized CSV adapter is supported. V1 targets species-specific distribution and locality expectations, excluding other check families and generic schema-driven validation. Place names do not provide exact coordinate boundaries; generated geographic approximations require review. No geographic lookup layer, intermediate constraint representation or semantic verifier is implemented. Generated code is not trusted automatically.

## Evaluation checkpoint

RQ1 reviews generated conditions against the frozen source, including qualifiers and geographic translations. RQ3 uses a small purposive case review with the raw public metadata; flags are not treated as confirmed errors, and obscured points are not treated as exact locations. Systematic RQ2 correctness evaluation is deferred; mutation-testing concepts remain a future evaluation option.
