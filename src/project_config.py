"""Shared loading and path resolution for experiment configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


def load_config(path: str | Path) -> tuple[dict[str, Any], Path]:
    """Load YAML and return it with the repository root used for paths."""
    config_path = Path(path).resolve()
    load_dotenv(config_path.parent.parent / ".env", override=False)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return config, config_path.parent.parent


def resolve_path(repo_root: Path, configured_path: str | Path) -> Path:
    """Resolve a config path relative to the repository root."""
    path = Path(configured_path)
    return path if path.is_absolute() else repo_root / path
