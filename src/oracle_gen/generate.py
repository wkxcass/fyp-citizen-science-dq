"""Generate a Python oracle using an OpenAI-compatible chat-completions API."""

from __future__ import annotations

import argparse
import ast
import os
import re
import tempfile
from pathlib import Path

import requests
from src.project_config import load_config, resolve_path
from src.qc_engine.schema import schema_description
from .prompting import build_prompt, fetch_wikipedia_text


class OracleGenerationError(RuntimeError):
    """Raised when the LLM response cannot become a valid oracle module."""


def extract_python(text: str) -> str:
    """Extract Python from a complete fenced or unfenced LLM response.

    A missing closing fence is treated as a likely truncated completion rather
    than silently writing invalid source code to the configured output path.
    """
    response = text.strip()
    if not response:
        raise OracleGenerationError("The LLM returned an empty response.")

    opening = re.search(r"```(?:python|py)?[ \t]*\r?\n", response, flags=re.IGNORECASE)
    if opening:
        body = response[opening.end():]
        closing = re.search(r"```", body)
        if not closing:
            raise OracleGenerationError(
                "The LLM response contains an unterminated code fence; "
                "the completion may have been truncated."
            )
        response = body[:closing.start()].strip()
    elif "```" in response:
        raise OracleGenerationError("The LLM response contains a malformed code fence.")

    if not response:
        raise OracleGenerationError("The LLM response contained no Python source.")
    return response + "\n"


def validate_oracle_source(source: str) -> None:
    """Check syntax and the required top-level oracle entry point."""
    try:
        tree = ast.parse(source, filename="<generated_oracle.py>")
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno else "an unknown line"
        raise OracleGenerationError(
            f"The generated oracle is not valid Python ({location}): {exc.msg}."
        ) from exc

    has_check_record = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "check_record"
        for node in tree.body
    )
    if not has_check_record:
        raise OracleGenerationError(
            "The generated oracle must define a top-level check_record function."
        )


def atomic_write_text(path: Path, content: str) -> None:
    """Write a completed artifact atomically so interruptions cannot leave a partial file."""
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(content)
        temporary_path.replace(path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def call_llm(
    prompt: str,
    model: str,
    base_url: str,
    api_key: str,
    max_output_tokens: int | None = None,
    timeout: int = 120,
) -> tuple[str, str | None]:
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }
    if max_output_tokens is not None:
        payload["max_tokens"] = max_output_tokens
    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    choice = response.json()["choices"][0]
    content = choice["message"]["content"]
    if not isinstance(content, str):
        raise OracleGenerationError("The LLM response content was not a text string.")
    return content, choice.get("finish_reason")


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
    api_key = os.getenv(oracle_config.get("api_key_env", "LLM_API_KEY"))
    if not api_key:
        raise SystemExit("LLM_API_KEY is required unless --prompt-only is used.")
    base_url = os.getenv("LLM_BASE_URL", oracle_config["base_url"])
    max_output_tokens = oracle_config.get("max_output_tokens")
    generated, finish_reason = call_llm(
        prompt,
        oracle_config["model"],
        base_url,
        api_key,
        max_output_tokens=int(max_output_tokens) if max_output_tokens is not None else None,
    )
    if finish_reason in {"length", "max_tokens"}:
        raise SystemExit(
            "Oracle generation stopped at the output-token limit. "
            "Increase oracle_generation.max_output_tokens in config/v0.yaml and retry."
        )
    try:
        source = extract_python(generated)
        validate_oracle_source(source)
    except OracleGenerationError as exc:
        raise SystemExit(f"Oracle generation failed: {exc}") from exc
    atomic_write_text(output_path, source)
    print(f"Wrote generated oracle to {output_path}")


if __name__ == "__main__":
    main()
