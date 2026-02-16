from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path

from .utils import repo_root


def validate_json_schema(
    json_path: Path,
    schema_path: Path,
    array_key: str,
    *,
    skip_type_check_fields: frozenset[str] = frozenset(),
    extra_item_validator: Callable[[int, dict, dict, list[str]], None] | None = None,
    extra_validator: Callable[[list, list[str]], None] | None = None,
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

    if not isinstance(data, dict):
        return ["root must be an object"]

    for key in schema.get("required", []):
        if key not in data:
            errors.append(f"missing required key: {key}")

    allowed_keys = set(schema.get("properties", {}).keys())
    if schema.get("additionalProperties") is False:
        for key in data:
            if key not in allowed_keys:
                errors.append(f"unexpected key: {key}")

    items = data.get(array_key)
    if items is not None:
        if not isinstance(items, list):
            errors.append(f"'{array_key}' must be an array")
        else:
            item_schema = (
                schema.get("properties", {}).get(array_key, {}).get("items", {})
            )
            required_fields = item_schema.get("required", [])
            allowed_fields = set(item_schema.get("properties", {}).keys())
            no_additional = item_schema.get("additionalProperties") is False

            for i, item in enumerate(items):
                if not isinstance(item, dict):
                    errors.append(f"{array_key}[{i}]: must be an object")
                    continue
                for field in required_fields:
                    if field not in item:
                        errors.append(f"{array_key}[{i}]: missing required field: {field}")
                if no_additional:
                    for key in item:
                        if key not in allowed_fields:
                            errors.append(f"{array_key}[{i}]: unexpected field: {key}")
                for field, prop_schema in item_schema.get("properties", {}).items():
                    if field not in item:
                        continue
                    val = item[field]
                    if field not in skip_type_check_fields:
                        if prop_schema.get("type") == "string" and not isinstance(
                            val, str
                        ):
                            errors.append(f"{array_key}[{i}].{field}: must be a string")
                    enum_vals = prop_schema.get("enum")
                    if enum_vals and val not in enum_vals:
                        errors.append(
                            f"{array_key}[{i}].{field}: must be one of {enum_vals}, got '{val}'"
                        )
                if extra_item_validator:
                    extra_item_validator(i, item, item_schema, errors)

            if extra_validator:
                extra_validator(items, errors)

    return errors


def validate_deps_schema() -> list[str]:
    def _item_validator(i: int, item: dict, item_schema: dict, errors: list[str]) -> None:
        depends = item.get("depends")
        if isinstance(depends, list):
            for dep_val in depends:
                if not isinstance(dep_val, str):
                    errors.append(f"checks[{i}].depends: items must be strings")

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
        "checks",
        extra_item_validator=_item_validator,
        extra_validator=_extra_validator,
    )


def validate_defaults_schema() -> list[str]:
    return validate_json_schema(
        repo_root() / "scripts" / "macos-defaults.json",
        repo_root() / "scripts" / "macos-defaults.schema.json",
        "defaults",
        skip_type_check_fields=frozenset({"value"}),
    )


def validate_links_schema() -> list[str]:
    return validate_json_schema(
        repo_root() / "scripts" / "links.json",
        repo_root() / "scripts" / "links.schema.json",
        "links",
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
