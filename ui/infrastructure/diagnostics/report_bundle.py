"""Crash report bundles on disk: one zip per report, `manifest.json` inside.

    <logs>/crash-reports/<report_id>.zip        waiting for the user's answer
    <logs>/crash-reports/sent/<report_id>.zip   sent (kept for reference, pruned)
    <logs>/crash-reports/dumps/*.dmp            written by the engine when the process dies

Pure file work: no Qt, no network, no idea of what a report means.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

MANIFEST = "manifest.json"
KEEP_SENT = 10
KEEP_PENDING = 10


def reports_dir(logs_dir: Path) -> Path:
    return logs_dir / "crash-reports"


def dumps_dir(logs_dir: Path) -> Path:
    path = reports_dir(logs_dir) / "dumps"
    path.mkdir(parents=True, exist_ok=True)
    return path


def tail(path: Path, lines: int = 400) -> str:
    """The last `lines` lines of a text file ("" when it does not exist)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""
    return "\n".join(text.splitlines()[-lines:])


def write_bundle(directory: Path, report_id: str, manifest: dict[str, object],
                 texts: dict[str, str], files: list[Path]) -> Path:
    """Writes `<report_id>.zip` with the manifest, the texts and the files (moved in, not copied)."""
    directory.mkdir(parents=True, exist_ok=True)
    bundle = directory / f"{report_id}.zip"
    temporary = bundle.with_suffix(".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
        for name, text in texts.items():
            archive.writestr(name, text)
        for path in files:
            archive.write(path, arcname=path.name)
    temporary.replace(bundle)
    for path in files:
        path.unlink(missing_ok=True)
    prune(directory, KEEP_PENDING)
    return bundle


def read_manifest(bundle: Path) -> dict[str, object]:
    with zipfile.ZipFile(bundle) as archive:
        return json.loads(archive.read(MANIFEST).decode("utf-8"))


def read_member(bundle: Path, name: str) -> bytes:
    with zipfile.ZipFile(bundle) as archive:
        return archive.read(name)


def pending_bundles(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.zip")) if directory.is_dir() else []


def mark_sent(bundle: Path) -> Path:
    sent = bundle.parent / "sent"
    sent.mkdir(parents=True, exist_ok=True)
    target = sent / bundle.name
    bundle.replace(target)
    prune(sent, KEEP_SENT)
    return target


def discard(bundle: Path) -> None:
    bundle.unlink(missing_ok=True)


def prune(directory: Path, keep: int) -> None:
    for old in sorted(directory.glob("*.zip"))[:-keep]:
        old.unlink(missing_ok=True)


def fresh_dumps(directory: Path) -> list[Path]:
    """Minidumps the engine wrote and no bundle took yet."""
    return sorted(directory.glob("*.dmp")) if directory.is_dir() else []
