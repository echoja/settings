from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path

import jsonschema

from .utils import repo_root


def validate_json_schema(
    json_path: Path,
    schema_path: Path,
    *,
    extra_validator: Callable[[list, list[str]], None] | None = None,
    array_key: str | None = None,
) -> list[str]:
    errors: list[str] = []

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"cannot load {json_path.name}: {exc}"]

    try:
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"cannot load schema: {exc}"]

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        errors.append(exc.message)

    if extra_validator and array_key:
        items = data.get(array_key)
        if isinstance(items, list):
            extra_validator(items, errors)

    return errors


def validate_deps_schema() -> list[str]:
    def _extra_validator(items: list, errors: list[str]) -> None:
        all_labels = {
            item["label"]
            for item in items
            if isinstance(item, dict) and "label" in item
        }
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for dep in item.get("depends", []):
                if dep not in all_labels:
                    errors.append(
                        f"checks[{i}].depends: unknown label '{dep}'"
                    )

        in_degree: dict[str, int] = defaultdict(int)
        dependents: dict[str, list[str]] = defaultdict(list)
        for item in items:
            if not isinstance(item, dict) or "label" not in item:
                continue
            label = item["label"]
            in_degree.setdefault(label, 0)
            for dep in item.get("depends", []):
                if dep in all_labels:
                    dependents[dep].append(label)
                    in_degree[label] += 1

        queue: deque[str] = deque(
            label for label, deg in in_degree.items() if deg == 0
        )
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for child in dependents[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if visited < len(in_degree):
            cycle_members = sorted(
                label for label, deg in in_degree.items() if deg > 0
            )
            errors.append(
                f"dependency cycle detected among: {', '.join(cycle_members)}"
            )

    return validate_json_schema(
        repo_root() / "scripts" / "deps.json",
        repo_root() / "scripts" / "deps.schema.json",
        array_key="checks",
        extra_validator=_extra_validator,
    )


def validate_defaults_schema() -> list[str]:
    return validate_json_schema(
        repo_root() / "scripts" / "macos-defaults.json",
        repo_root() / "scripts" / "macos-defaults.schema.json",
    )


def validate_links_schema() -> list[str]:
    return validate_json_schema(
        repo_root() / "scripts" / "links.json",
        repo_root() / "scripts" / "links.schema.json",
    )


def check_json_formatting(file_path: Path) -> bool:
    with open(file_path, encoding="utf-8") as f:
        raw = f.read()
    data = json.loads(raw)
    expected = json.dumps(data, indent=2) + "\n"
    return raw == expected


def check_hardcoded_paths(file_path: Path) -> list[tuple[int, str]]:
    regex = re.compile(r"/(Users|home)/[^\s/]+")
    violations: list[tuple[int, str]] = []
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        for lineno, line in enumerate(f, start=1):
            if regex.search(line):
                violations.append((lineno, line.rstrip()))
    return violations
