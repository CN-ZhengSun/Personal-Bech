"""Logcat text parsing and process/package metadata helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence


_THREADTIME_RE = re.compile(
    r"^(?P<date>(?:\d{4}-)?\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2}\.\d+)\s+"
    r"(?:(?P<uid>\S+)\s+)?"
    r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+"
    r"(?P<level>[VDIWEF])\s+(?P<body>.*)$"
)
_PACKAGE_UID_RE = re.compile(r"^package:(?P<package>\S+)\s+uid:(?P<uid>\d+)\s*$")
_ANDROID_APP_UID_RE = re.compile(r"^u(?P<user>\d+)_a(?P<app>\d+)$")


def _normalize_uid(uid: str) -> str:
    match = _ANDROID_APP_UID_RE.match(uid)
    if not match:
        return uid
    return str(int(match.group("user")) * 100000 + 10000 + int(match.group("app")))


def parse_threadtime_line(line: str) -> dict | None:
    """Parse logcat ``threadtime`` output, with optional year and UID modifiers."""
    match = _THREADTIME_RE.match(line)
    if not match:
        return None

    body = match.group("body")
    tag, separator, message = body.partition(":")
    if not separator:
        tag, message = "", body

    return {
        "timestamp": f'{match.group("date")} {match.group("time")}',
        "uid": match.group("uid") or "",
        "pid": match.group("pid"),
        "tid": match.group("tid"),
        "level": match.group("level"),
        "tag": tag.strip(),
        "message": message.lstrip(),
    }


def parse_package_uid_output(output: str) -> dict[str, tuple[str, ...]]:
    """Return UID -> package names from ``cmd package list packages -U`` output."""
    packages: dict[str, list[str]] = {}
    for line in output.splitlines():
        match = _PACKAGE_UID_RE.match(line.strip())
        if not match:
            continue
        uid = match.group("uid")
        package = match.group("package")
        if package not in packages.setdefault(uid, []):
            packages[uid].append(package)
    return {uid: tuple(names) for uid, names in packages.items()}


def parse_process_output(output: str) -> dict[str, str]:
    """Return PID -> process name from Android toybox ``ps -A`` output."""
    processes: dict[str, str] = {}
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        pid, name = parts[1], parts[-1]
        if pid.isdigit() and not name.startswith("[") and name not in ("NAME", "COMMAND"):
            processes[pid] = name
    return processes


def build_log_record(
    line: str,
    packages_by_uid: Mapping[str, Sequence[str]],
    processes_by_pid: Mapping[str, str],
) -> dict:
    """Create the structured record sent over the Logcat WebSocket."""
    parsed = parse_threadtime_line(line)
    if parsed is None:
        return {"type": "log", "raw": line, "parsed": False}

    package_names = list(packages_by_uid.get(_normalize_uid(parsed["uid"]), ()))
    process_name = processes_by_pid.get(parsed["pid"], "")
    process_package = process_name.split(":", 1)[0]
    application_id = process_package if process_package in package_names else ""
    if not application_id and len(package_names) == 1:
        application_id = package_names[0]
    if not process_name:
        process_name = application_id

    return {
        "type": "log",
        "raw": line,
        "parsed": True,
        **parsed,
        "application_id": application_id,
        "package_names": package_names,
        "process_name": process_name,
    }
