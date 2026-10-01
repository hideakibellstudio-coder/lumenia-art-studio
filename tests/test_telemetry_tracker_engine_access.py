"""The telemetry screens reach the engine through the tracker, and only through its telemetry role.

Until 2026-10-01 the panel, the grid cockpit, the diagnostics dialog and the tracker itself each asked
the global registry for the whole `EngineBackend` (14 lookups in 7 files) to flip a switch or read a
snapshot. The tracker is the single source of the telemetry session, so it is now also the single door
to the engine for it: it takes a provider that returns only a `TelemetryProtocol`.
"""

from __future__ import annotations

from ui.core.engine.backend_protocols import TelemetryProtocol
from ui.core.engine.telemetry_dto import TelemetrySnapshot
from ui.core.engine.telemetry_tracker import TelemetryTracker


class FakeTelemetry:
    """Only the telemetry role of the engine: anything else would raise AttributeError."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.summary = False
        self.detailed = False
        self.snapshot = TelemetrySnapshot()

    def set_telemetry_enabled(self, enabled: bool) -> None:
        self.calls.append(("set_telemetry_enabled", enabled))
        self.summary = enabled

    def is_telemetry_enabled(self) -> bool:
        return self.summary

    def set_detailed_logging_enabled(self, enabled: bool) -> None:
        self.calls.append(("set_detailed_logging_enabled", enabled))
        self.detailed = enabled

    def is_detailed_logging_enabled(self) -> bool:
        return self.detailed

    def reset_telemetry(self) -> None:
        self.calls.append(("reset_telemetry",))

    def get_telemetry_snapshot(self) -> TelemetrySnapshot:
        return self.snapshot


def test_the_fake_is_what_the_telemetry_role_asks_for():
    """If the role grows, the fake must grow with it, or this test names the member."""
    members = [name for name in dir(TelemetryProtocol) if not name.startswith("_")]
    missing = [name for name in members if not hasattr(FakeTelemetry(), name)]
    assert not missing, f"the telemetry role has members the test double lacks: {missing}"


def test_the_switches_and_the_snapshot_go_through_the_provider():
    engine = FakeTelemetry()
    tracker = TelemetryTracker(engine=lambda: engine)

    tracker.enable_capture()
    tracker.set_detailed_log(True)
    tracker.reset_engine()

    assert tracker.stroke_summary_enabled() and tracker.detailed_log_enabled()
    assert tracker.read_snapshot() is engine.snapshot
    assert engine.calls == [("set_telemetry_enabled", True), ("set_detailed_logging_enabled", True), ("reset_telemetry",)]


def test_without_an_engine_every_call_is_a_quiet_no_op_and_the_snapshot_is_none():
    tracker = TelemetryTracker(engine=lambda: None)

    tracker.enable_capture(False)
    tracker.set_detailed_log(True)
    tracker.reset_engine()

    assert tracker.read_snapshot() is None
    assert not tracker.stroke_summary_enabled() and not tracker.detailed_log_enabled()


def test_the_report_falls_back_to_the_last_reading_when_the_engine_is_gone():
    holder = [FakeTelemetry()]
    tracker = TelemetryTracker(engine=lambda: holder[0])
    tracker.update(tracker.read_snapshot(), {})
    holder[0] = None  # the engine went away after a reading

    report = tracker.generate_full_report(stay_on_top=False)

    assert "PIPELINE" in report.upper()
