"""Prompt assembly and knowledge-source retrieval."""

from pathlib import Path
from typing import Any
import requests

from src.project_config import USER_AGENT


def fetch_wikipedia_text(url: str, timeout: int = 30) -> str:
    title = url.rstrip("/").split("/")[-1]
    endpoint = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    response = requests.get(endpoint, timeout=timeout, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.json().get("extract", "")


def load_prompt_template(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_prompt(template_path: str | Path, values: dict[str, Any]) -> str:
    return load_prompt_template(template_path).format(**values)
