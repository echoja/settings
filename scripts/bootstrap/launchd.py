from __future__ import annotations

import json
import os
import plistlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .utils import repo_root


@dataclass(frozen=True)
class JobEntry:
    label: str
    description: str
    script: str
    schedule: dict[str, int]
    environment: dict[str, str] = field(default_factory=dict)
    log: str | None = None


def load_job_entries() -> list[JobEntry]:
    jobs_file = repo_root() / "scripts" / "jobs.json"
    with open(jobs_file, encoding="utf-8") as f:
        data = json.load(f)
    return [
        JobEntry(
            label=item["label"],
            description=item["description"],
            script=item["script"],
            schedule=item["schedule"],
            environment=item.get("environment", {}),
            log=item.get("log"),
        )
        for item in data["jobs"]
    ]


def generate_plist(entry: JobEntry) -> dict:
    root = repo_root()
    script_path = str(root / entry.script)

    plist: dict = {
        "Label": entry.label,
        "ProgramArguments": ["/bin/bash", script_path],
        "WorkingDirectory": str(root),
    }

    if "interval" in entry.schedule:
        plist["StartInterval"] = entry.schedule["interval"]
    else:
        cal: dict[str, int] = {}
        key_map = {
            "month": "Month",
            "day": "Day",
            "weekday": "Weekday",
            "hour": "Hour",
            "minute": "Minute",
        }
        for k, plist_key in key_map.items():
            if k in entry.schedule:
                cal[plist_key] = entry.schedule[k]
        if cal:
            plist["StartCalendarInterval"] = cal

    if entry.environment:
        plist["EnvironmentVariables"] = dict(entry.environment)

    log_path = entry.log or str(
        Path.home() / "Library" / "Logs" / f"{entry.label}.log"
    )
    plist["StandardOutPath"] = log_path
    plist["StandardErrorPath"] = log_path

    return plist


def _plist_path(label: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def write_plist(entry: JobEntry) -> Path:
    path = _plist_path(entry.label)
    path.parent.mkdir(parents=True, exist_ok=True)
    plist_data = generate_plist(entry)
    with open(path, "wb") as f:
        plistlib.dump(plist_data, f)
    return path


def is_plist_current(entry: JobEntry) -> bool:
    path = _plist_path(entry.label)
    if not path.is_file():
        return False
    try:
        with open(path, "rb") as f:
            on_disk = plistlib.load(f)
    except Exception:
        return False
    return on_disk == generate_plist(entry)


def is_job_loaded(label: str) -> bool:
    uid = os.getuid()
    r = subprocess.run(
        ["launchctl", "print", f"gui/{uid}/{label}"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def is_script_present(entry: JobEntry) -> bool:
    return (repo_root() / entry.script).is_file()


def is_script_executable(entry: JobEntry) -> bool:
    path = repo_root() / entry.script
    return path.is_file() and os.access(path, os.X_OK)


def bootstrap_job(label: str) -> subprocess.CompletedProcess[str]:
    uid = os.getuid()
    path = _plist_path(label)
    return subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(path)],
        capture_output=True,
        text=True,
    )


def bootout_job(label: str) -> subprocess.CompletedProcess[str]:
    uid = os.getuid()
    return subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}/{label}"],
        capture_output=True,
        text=True,
    )
