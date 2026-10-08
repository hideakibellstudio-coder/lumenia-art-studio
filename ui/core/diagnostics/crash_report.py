"""A crash report: the facts about one fall, gathered on this machine.

`CrashReport` is what is shown to the user and what goes into the report
bundle's `manifest.json`. The files themselves (minidump, native stack, log tail)
are collected by `ui/infrastructure/diagnostics/`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class CrashKind(str, Enum):
    NATIVE = "native"        # the process died (engine or Qt): native stack and, on Windows, a minidump
    PYTHON = "python"        # an unhandled Python exception; the program kept running
    MANUAL = "manual"        # "Help > Create diagnostic report": the user asked for one


@dataclass(frozen=True)
class CrashReport:
    report_id: str            # "20261008-142301-native", also the bundle's file name
    kind: CrashKind
    created_at: str           # ISO timestamp, local time
    app_version: str
    update_channel: str
    platform: str             # "Windows-11-10.0.26100-SP0"
    python_version: str
    engine_simd: str = ""
    summary: str = ""         # first line of the exception or the native fault
    files: tuple[str, ...] = field(default_factory=tuple)  # names inside the bundle

    def to_manifest(self) -> dict[str, object]:
        data = asdict(self)
        data["kind"] = self.kind.value
        data["files"] = list(self.files)
        data["schema_version"] = 1
        return data

    @classmethod
    def from_manifest(cls, data: dict[str, object]) -> "CrashReport":
        return cls(report_id=str(data["report_id"]), kind=CrashKind(str(data["kind"])),
                   created_at=str(data["created_at"]), app_version=str(data["app_version"]),
                   update_channel=str(data.get("update_channel", "")), platform=str(data.get("platform", "")),
                   python_version=str(data.get("python_version", "")), engine_simd=str(data.get("engine_simd", "")),
                   summary=str(data.get("summary", "")), files=tuple(str(f) for f in data.get("files", ()) or ()))
