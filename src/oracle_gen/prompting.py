"""Prompt assembly and knowledge-source retrieval."""

from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import requests

from src.project_config import USER_AGENT


def fetch_wikipedia_text(url: str, timeout: int = 30) -> str:
    """Fetch article prose, including sections beyond the introductory summary.

    Keep section headings and do not impose a character/sentence limit or fall
    back to the summary: geographic evidence often appears later in an article.
    TextExtracts omits some non-prose content, such as infoboxes and maps.
    """
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or not parsed.hostname.endswith(".wikipedia.org")
        or not parsed.path.startswith("/wiki/")
    ):
        raise ValueError("Expected a Wikipedia article URL such as https://en.wikipedia.org/wiki/Sunda_pangolin.")
    title = unquote(parsed.path[len("/wiki/"):].rstrip("/")).replace("_", " ")
    if not title:
        raise ValueError("The Wikipedia article URL must include a page title.")
    endpoint = f"https://{parsed.hostname}/w/api.php"
    response = requests.get(
        endpoint,
        params={
            "action": "query",
            "prop": "extracts",
            "titles": title,
            "redirects": 1,
            "explaintext": 1,
            "exsectionformat": "wiki",
            "format": "json",
            "formatversion": 2,
        },
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise ValueError(f"Wikipedia API error: {payload['error'].get('info', payload['error'])}")
    pages = payload.get("query", {}).get("pages", [])
    if len(pages) != 1 or "missing" in pages[0] or "invalid" in pages[0]:
        raise ValueError(f"Wikipedia article not found: {url}")
    text = pages[0].get("extract")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"Wikipedia returned no article text for {url}; no prompt was generated.")
    return text


def load_prompt_template(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_prompt(template_path: str | Path, values: dict[str, Any]) -> str:
    return load_prompt_template(template_path).format(**values)
