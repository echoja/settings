from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path

from .utils import repo_root

KIND_PREDICATE: dict[str, Callable[[str], object]] = {
    "command": shutil.which,
    "dir": os.path.isdir,
    "file": os.path.isfile,
}


def load_dep_checks() -> list[dict]:
    checks_file = repo_root() / "scripts" / "deps.json"
    with open(checks_file, encoding="utf-8") as f:
        data = json.load(f)
    home = str(Path.home())
    for check in data["checks"]:
        check["target"] = check["target"].replace("$HOME", home)
    return data["checks"]
