# V0 oracle-generation prompt

You are generating a transparent, executable Python data-quality oracle.

Species: {common_name} ({scientific_name})
Knowledge source: {knowledge_source_url}

Knowledge source text:
{knowledge_text}

Dataset schema:
{dataset_schema}

Generate a Python module defining exactly:

    def check_record(record: dict) -> list[dict[str, str]]:

Return an empty list when there is no applicable violation. For each possible violation return a dictionary containing flag_code and reason. Start with ecological and spatial constraints, but identify adjacent potentially testable concepts in one or two brief comments if they cannot be implemented using the supplied schema. Do not invent fields or facts. Treat probabilistic ecological tendencies as candidates for review, not absolute violations. Missing values should normally be skipped.

Return only Python source, without Markdown code fences or explanatory prose. Do not access the network, filesystem, subprocesses, or environment variables. Do not modify records. Keep the implementation concise, deterministic, and readable.
