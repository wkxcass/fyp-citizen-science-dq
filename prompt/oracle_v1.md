# v1 spatial oracle-generation prompt

You are generating a transparent, executable Python data-quality oracle for reviewing species occurrence records.

Species: {common_name} ({scientific_name})
Knowledge source: {knowledge_source_url}

Knowledge source text:
{knowledge_text}

Dataset schema:
{dataset_schema}

## Task and scope

Generate species-specific geographic review checks supported by the supplied species text. Spatial/geographical constraints concern where a species is documented to occur, including named countries, regions, islands or localities.

Derive candidate expectations from the species text first, independently of the dataset schema. Then use the schema to determine whether and how each source-supported expectation can be tested. A field's presence alone must not justify a condition. Perform this reasoning internally; return only the executable module.

- Preserve the source's scope, qualifiers and uncertainty, including current versus historical distribution and native versus introduced occurrence. Do not treat an occurrence outside the native range as inconsistent if the source also documents introduced occurrence there.
- Do not infer global absence from a statement about one locality, or treat examples of occurrence locations as an exhaustive range. Probabilistic tendencies and incomplete distribution accounts do not establish absolute exclusions.
- Exclude habitat, elevation and other checks requiring unavailable external evidence. Exclude non-geographic check families, including seasonal, breeding and morphological checks.
- Exclude generic quality-grade, observer, taxon-name and other schema-driven validation. Coordinate usability guards support geographic assessment; they must not produce separate data-quality flags.
- Do not invent fields, species facts or distribution claims. Use only the supplied record fields as runtime evidence; do not assume access to raw API responses, uncertainty metadata or geographic datasets absent from the schema.

## Geographic implementation

A place name is not itself a coordinate boundary. Do not invent precise coordinate boundaries for vague named regions, or present a bounding rectangle as an exact country, island or species-range polygon. Implement a geographic condition only when its translation to the available record fields is defensible from the supplied information. Do not build or call a geographic lookup service.

If a defensible coarse approximation is used, keep its bounds explicit and readable in the code, and identify the approximation and its limits in the flag's reason. Preserve geographic distinctions that affect the expectation. If the translation cannot be justified, omit that condition rather than forcing a check. If no supported geographic condition is implementable, define the required function and return an empty list.

## Runtime and output contract

Generate a Python module defining exactly this entry point:

    def check_record(record: dict) -> list[dict[str, str]]:

Fields declared as number or integer are provided as float/int, or None if missing. Fields declared as string or date are provided as str, or None if missing. Unparseable but present numeric values may remain strings after normalization; handle them without raising an exception.

Skip a geographic assessment when its required coordinates are missing or unusable, including malformed values, non-finite numbers or values outside valid latitude/longitude limits. Do not flag these as species-distribution inconsistencies, substitute zero coordinates, or invent an uncertainty allowance. A supplied point does not establish an exact location or independently verify a wild occurrence.

Return an empty list when no applicable geographic review flag is raised, including when required evidence is unavailable. For each possible geographic inconsistency, return a dictionary containing only flag_code and reason, both strings. Use a stable, descriptive flag_code. Keep the reason concise and connect it to the source-supported geographic expectation; identify any geographic approximation used. Describe flags as candidates for review, not confirmed biological errors or proof of absence.

Return only Python source, without Markdown code fences or explanatory prose. Omit code comments, docstrings and commentary about unimplemented or adjacent check families. Do not add metadata fields or change the return structure. Do not access the network, filesystem, subprocesses or environment variables. Do not modify records. Keep the implementation concise, deterministic and readable, using only the Python standard library if imports are needed.
