# Prototype V0 Architecture

V0 is an explicit pipeline:

1. Fetch the Wikipedia summary for *Presbytis femoralis*.
2. Combine that text with the normalized iNaturalist CSV schema and oracle contract.
3. Optionally call an OpenAI-compatible chat-completions endpoint and save the response as Python.
4. Resolve the species through iNaturalist, fetch observations, and normalize them into CSV.
5. Load an oracle, call check_record(record) for each row, and write one output row per flag.

The checked-in reference oracle exercises the QC mechanics without an LLM or live API. It is a test harness, not the research result.

## Oracle contract

    def check_record(record: dict) -> list[dict[str, str]]:
        ...

An empty list means no applicable violation. A returned dictionary contains a stable flag_code and human-readable reason. Missing values are normally treated as inapplicable. V0 flags for human review; it does not automatically clean, correct, or delete records.

## Deliberate boundaries

Only a normalized CSV adapter is supported. The initial target is ecological and spatial knowledge. Adjacent concepts may be noted but are not required to be executable. Generated code is not trusted automatically. No intermediate constraint representation or semantic verifier is implemented yet.
