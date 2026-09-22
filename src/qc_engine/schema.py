"""Schema representation and source-field extraction for V0."""

from __future__ import annotations

import re
from typing import Any


def schema_fields(config: dict[str, Any]) -> list[dict[str, Any]]:
    return config["dataset"]["schema"]["fields"]


def schema_description(config: dict[str, Any]) -> str:
    schema = config["dataset"]["schema"]
    lines = [f"Schema id: {schema['id']}", schema.get("description", "")]
    for field in schema_fields(config):
        lines.append(f"- {field['name']} ({field['type']}): {field.get('description', '')}")
    return "\n".join(line for line in lines if line)


def get_source_value(value: Any, source: str) -> Any:
    """Read dotted and indexed paths such as geojson.coordinates[1]."""
    current = value
    for token in re.findall(r"[^.\[\]]+|\[\d+\]", source):
        key: str | int = int(token[1:-1]) if token.startswith("[") else token
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(key)]
            except (IndexError, TypeError):
                return None
        else:
            return None
    return current


def normalize_observation(observation: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Map an iNaturalist response to the configured normalized schema."""
    normalized: dict[str, Any] = {}
    for field in schema_fields(config):
        value = get_source_value(observation, field["source"])
        if field.get("transform") == "observation_url" and value is not None:
            value = f"https://www.inaturalist.org/observations/{value}"
        normalized[field["name"]] = value
    return normalized


def coerce_value(raw: Any, field_type: str) -> Any:
    """Coerce a raw CSV string to the type declared for a schema field.

    Missing values (None or empty string) become None. Values that fail to
    parse as their declared type are returned unchanged — a malformed value
    is a distinct condition from a missing one, and collapsing the two would
    let corrupt input silently masquerade as an ordinarily-absent field.
    """
    if raw is None or raw == "":
        return None
    if field_type == "integer":
        try:
            return int(raw)
        except (TypeError, ValueError):
            return raw
    if field_type == "number":
        try:
            return float(raw)
        except (TypeError, ValueError):
            return raw
    return raw


def normalize_record(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Coerce a raw CSV row to the types declared in the configured schema.

    csv.DictReader always returns strings; this makes the runtime types seen
    by check_record match what schema_description() tells the LLM to expect.
    """
    field_types = {field["name"]: field["type"] for field in schema_fields(config)}
    return {
        key: coerce_value(value, field_types[key]) if key in field_types else value
        for key, value in record.items()
    }


def schema_column_names(config: dict[str, Any]) -> list[str]:
    return [field["name"] for field in schema_fields(config)]
