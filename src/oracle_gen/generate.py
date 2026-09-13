"""Generate a Python oracle using an OpenAI-compatible chat-completions API."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

import requests
import yaml

from src.project_config import load_config, resolve_path
from src.qc_engine.schema import schema_description
from .prompting import build_prompt, fetch_wikipedia_text


def extract_python(text: str) -> str:
    match = re.search(r"```python\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip() + "\n"
    match = re.search(r"```\s*(.*?)```", text, flags=re.DOTALL)
    if match:
        return match.group(1).strip() + "\n"
    return text.strip() + "\n"


def call_llm(prompt: str, model: str, base_url: str, api_key: str, timeout: int = 120) -> str:
    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/v0.yaml")
    parser.add_argument("--prompt-only", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    config, repo_root = load_config(args.config)
    species, source = config["species"], config["knowledge_source"]
    oracle_config = config["oracle_generation"]
    knowledge = fetch_wikipedia_text(source["url"])
    schema = schema_description(config)
    prompt_template_path = resolve_path(repo_root, oracle_config["prompt_path"])
    prompt = build_prompt(prompt_template_path, {
        "common_name": species["common_name"], "scientific_name": species["scientific_name"],
        "knowledge_source_url": source["url"], "knowledge_text": knowledge, "dataset_schema": schema,
    })
    output_path = Path(args.output) if args.output else resolve_path(repo_root, oracle_config["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.prompt_only:
        prompt_path = output_path.with_suffix(".prompt.txt")
        prompt_path.write_text(prompt, encoding="utf-8")
        print(f"Wrote prompt to {prompt_path}")
        return
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise SystemExit("LLM_API_KEY is required unless --prompt-only is used.")
    generated = call_llm(prompt, oracle_config["model"], os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"), api_key)
    output_path.write_text(extract_python(generated), encoding="utf-8")
    print(f"Wrote generated oracle to {output_path}")


if __name__ == "__main__":
    main()
