"""Request-template loading for the STRATZ GraphQL collector."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .aggregate import DataShapeError


def _substitute(value: Any, substitutions: dict[str, str | int]) -> Any:
    if isinstance(value, str):
        if value.startswith("{{") and value.endswith("}}") and value[2:-2] in substitutions:
            return substitutions[value[2:-2]]
        for key, replacement in substitutions.items():
            value = value.replace(f"{{{{{key}}}}}", str(replacement))
        return value
    if isinstance(value, list):
        return [_substitute(item, substitutions) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, substitutions) for key, item in value.items()}
    return value


def _path_get(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not part:
            raise DataShapeError("records_path must not contain empty segments")
        if not isinstance(current, dict) or part not in current:
            raise DataShapeError(f"records_path does not exist in GraphQL response: {path}")
        current = current[part]
    return current


@dataclass(frozen=True)
class RequestTemplate:
    """The project-specific query and response mapping, kept out of Python code."""

    query: str
    variables: dict[str, Any]
    records_path: str
    hero_id_field: str
    pair_id_field: str
    vs_field: str
    with_field: str
    synergy_field: str = "synergy"
    match_count_field: str = "matchCount"

    @classmethod
    def from_file(cls, path: Path) -> "RequestTemplate":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataShapeError(f"cannot read request template {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise DataShapeError("request template root must be an object")
        required = {
            "query", "variables", "records_path", "hero_id_field", "pair_id_field",
            "vs_field", "with_field",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise DataShapeError(f"request template is missing: {', '.join(missing)}")
        if not isinstance(raw["query"], str) or not raw["query"].strip():
            raise DataShapeError("request template query must be a non-empty string")
        if not isinstance(raw["variables"], dict):
            raise DataShapeError("request template variables must be an object")
        return cls(**{key: raw[key] for key in cls.__dataclass_fields__ if key in raw})

    def payload(self, substitutions: dict[str, str | int]) -> dict[str, Any]:
        return {"query": self.query, "variables": _substitute(self.variables, substitutions)}

    def records_from(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        records = _path_get(response, self.records_path)
        if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
            raise DataShapeError(f"{self.records_path} must resolve to a list of objects")
        return records
