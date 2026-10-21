from pathlib import Path
from unittest.mock import Mock

import pytest

from src.oracle_gen.generate import (
    OracleGenerationError,
    extract_python,
    main,
    validate_oracle_source,
)


def test_extract_python_removes_complete_code_fence():
    response = "```python\ndef check_record(record):\n    return []\n```"
    assert extract_python(response) == "def check_record(record):\n    return []\n"


def test_extract_python_rejects_unterminated_code_fence():
    response = "```python\ndef check_record(record):\n    return [\n"
    with pytest.raises(OracleGenerationError, match="unterminated code fence"):
        extract_python(response)


def test_validate_oracle_source_requires_valid_check_record():
    validate_oracle_source("def check_record(record):\n    return []\n")

    with pytest.raises(OracleGenerationError, match="not valid Python"):
        validate_oracle_source("def check_record(record):\n    return [\n")

    with pytest.raises(OracleGenerationError, match="must define a top-level check_record"):
        validate_oracle_source("def other(record):\n    return []\n")


ROOT = Path(__file__).parents[1]
ARTICLE = "Source introduction.\n\n== Distribution and habitat ==\nGeographic evidence from a later section."


@pytest.mark.parametrize("species", ["langur", "pangolin", "hornbill", "bulbul"])
def test_v1_prompt_only_contains_and_saves_full_article(tmp_path, monkeypatch, species):
    output = tmp_path / species / "oracle.py"
    monkeypatch.setattr("sys.argv", [
        "generate", "--config", str(ROOT / f"config/v1_{species}.yaml"),
        "--prompt-only", "--output", str(output),
    ])
    response = Mock()
    response.json.return_value = {"query": {"pages": [{"extract": ARTICLE}]}}
    monkeypatch.setattr("src.oracle_gen.prompting.requests.get", Mock(return_value=response))
    llm = Mock(side_effect=AssertionError("Prompt-only must not call the LLM"))
    monkeypatch.setattr("src.oracle_gen.generate.call_llm", llm)

    main()

    assert output.with_suffix(".knowledge.txt").read_text(encoding="utf-8") == ARTICLE
    assert ARTICLE in output.with_suffix(".prompt.txt").read_text(encoding="utf-8")
    assert not output.exists()
    llm.assert_not_called()


def test_generation_reuses_frozen_knowledge_without_fetching(tmp_path, monkeypatch):
    frozen = tmp_path / "frozen.txt"
    frozen.write_text(ARTICLE, encoding="utf-8")
    output = tmp_path / "run_02.py"
    monkeypatch.setattr("sys.argv", [
        "generate", "--config", str(ROOT / "config/v1_pangolin.yaml"),
        "--knowledge-file", str(frozen), "--output", str(output),
    ])
    fetch = Mock(side_effect=AssertionError("Frozen input must not fetch Wikipedia"))
    monkeypatch.setattr("src.oracle_gen.generate.fetch_wikipedia_text", fetch)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    source = "def check_record(record):\n    return []\n"
    llm = Mock(return_value=(source, "stop"))
    monkeypatch.setattr("src.oracle_gen.generate.call_llm", llm)

    main()

    prompt = output.with_suffix(".prompt.txt").read_text(encoding="utf-8")
    assert ARTICLE in prompt
    assert llm.call_args.args[0] == prompt
    assert output.with_suffix(".knowledge.txt").read_text(encoding="utf-8") == ARTICLE
    assert output.read_text(encoding="utf-8") == source
    fetch.assert_not_called()


@pytest.mark.parametrize("failure", ["empty_file", "missing_article"])
def test_bad_knowledge_preserves_existing_artifacts(tmp_path, monkeypatch, failure):
    output = tmp_path / "oracle.py"
    paths = [output, output.with_suffix(".knowledge.txt"), output.with_suffix(".prompt.txt")]
    for path in paths:
        path.write_text("previous artifact", encoding="utf-8")
    argv = ["generate", "--config", str(ROOT / "config/v1_pangolin.yaml"), "--output", str(output)]
    if failure == "empty_file":
        frozen = tmp_path / "empty.txt"
        frozen.write_text(" \n", encoding="utf-8")
        argv += ["--knowledge-file", str(frozen)]
    else:
        monkeypatch.setattr("src.oracle_gen.generate.fetch_wikipedia_text", Mock(side_effect=ValueError("not found")))
    monkeypatch.setattr("sys.argv", argv)
    llm = Mock()
    monkeypatch.setattr("src.oracle_gen.generate.call_llm", llm)

    with pytest.raises(SystemExit, match="Knowledge-source retrieval failed"):
        main()

    assert all(path.read_text(encoding="utf-8") == "previous artifact" for path in paths)
    llm.assert_not_called()
