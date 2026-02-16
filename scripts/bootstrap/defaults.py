from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .utils import repo_root


class ReadStatus(str, Enum):
    ok = "ok"
    key_missing = "key_missing"
    domain_missing = "domain_missing"


@dataclass(frozen=True)
class DefaultEntry:
    domain: str
    key: str
    type: str
    value: object
    description: str
    category: str
    restart: str | None = None


def load_defaults_entries() -> list[DefaultEntry]:
    defaults_file = repo_root() / "scripts" / "macos-defaults.json"
    with open(defaults_file, encoding="utf-8") as f:
        data = json.load(f)
    return [
        DefaultEntry(
            domain=item["domain"],
            key=item["key"],
            type=item["type"],
            value=item["value"],
            description=item["description"],
            category=item["category"],
            restart=item.get("restart"),
        )
        for item in data["defaults"]
    ]


def run_defaults_cmd(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["defaults", *args],
        capture_output=True, text=True,
    )


def read_default(domain: str, key: str) -> tuple[ReadStatus, str | None]:
    r = run_defaults_cmd("read", domain, key)
    if r.returncode != 0:
        stderr = r.stderr.strip()
        if "does not exist" in stderr:
            if "domain" in stderr.split("does not exist")[0].lower():
                return ReadStatus.domain_missing, None
            return ReadStatus.key_missing, None
        return ReadStatus.key_missing, None
    return ReadStatus.ok, r.stdout.strip()


def parse_default_value(raw: str, type_: str) -> object:
    if type_ == "bool":
        return raw.strip() in {"1", "true", "YES"}
    if type_ == "int":
        return int(raw.strip())
    if type_ == "float":
        return float(raw.strip())
    return raw.strip()


def format_write_value(value: object, type_: str) -> list[str]:
    if type_ == "bool":
        return ["-bool", "TRUE" if value else "FALSE"]
    if type_ == "int":
        return ["-int", str(value)]
    if type_ == "float":
        return ["-float", str(value)]
    return ["-string", str(value)]


def values_equal(a: object, b: object, type_: str) -> bool:
    if type_ == "bool":
        return bool(a) == bool(b)
    if type_ == "float":
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-9)
        except (TypeError, ValueError):
            return False
    return a == b
