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
            current = current[int(key)]
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


def schema_column_names(config: dict[str, Any]) -> list[str]:
    return [field["name"] for field in schema_fields(config)]
