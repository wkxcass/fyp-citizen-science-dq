import pytest

from src.oracle_gen.generate import (
    OracleGenerationError,
    extract_python,
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
