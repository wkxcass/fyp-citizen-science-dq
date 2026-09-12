"""Prompt assembly and knowledge-source retrieval for V0."""

from pathlib import Path
from typing import Any
import requests


def fetch_wikipedia_text(url: str, timeout: int = 30) -> str:
    title = url.rstrip("/").split("/")[-1]
    endpoint = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    response = requests.get(endpoint, timeout=timeout, headers={"User-Agent": "fyp-citizen-science-dq/0.1"})
    response.raise_for_status()
    return response.json().get("extract", "")


def load_prompt_template(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_prompt(template_path: str | Path, values: dict[str, Any]) -> str:
    return load_prompt_template(template_path).format(**values)
