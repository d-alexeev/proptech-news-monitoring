from __future__ import annotations

import pathlib
from typing import Any

import yaml


def repo_root_from(path: str | None) -> pathlib.Path:
    if path:
        return pathlib.Path(path).resolve()
    return pathlib.Path(__file__).resolve().parents[2]


def read_yaml(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be an object: {path}")
    return data
