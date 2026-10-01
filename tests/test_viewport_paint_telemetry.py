"""The "Blit" meter counts the canvas copy, not only the drawImage call (D16, found 2026-09-26).

The meter called "6. Apresentação Blit Qt" timed `QPainter.drawImage` and nothing
else. The copy of the canvas to a QImage (`get_qimage_lod`), the biggest cost of a
repaint (34 ms at 4K on 2026-10-01, the cost of D4), ran before the timer, and
`qt_paint_total_ms` was published with no meter that showed it.

The painter now times the acquisition on its own, and every screen reads the
presentation cost from one formula (`presentation_ms`).
"""

from __future__ import annotations

import time

import pytest

from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.core.engine.telemetry_dto import TelemetrySnapshot
from ui.core.engine.telemetry_meters import METERS, presentation_ms, read_meters
from ui.core.engine.telemetry_tracker import TelemetryTracker

SLOW_COPY_S = 0.030


@pytest.fixture
def painted_viewport(qapp):
    """A real RenderWidget over a real engine whose canvas copy takes SLOW_COPY_S."""
    pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")
    from ui.infrastructure.bridge_client.aladyn import AladynBackend
    from ui.plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget

    class SlowCopyBackend(AladynBackend):
        def get_qimage_lod(self, zoom):
            time.sleep(SLOW_COPY_S)
            return super().get_qimage_lod(zoom)

    registry = EngineRegistry.instance()
    previous = registry.get_backend()
    backend = SlowCopyBackend()
    registry.set_backend(backend)
    document = DocumentManager.instance().new_document(64, 64, name="telemetry", activate=True)
    backend.set_active_document_context(document.uid, 64, 64)
    widget = RenderWidget()
    widget.resize(200, 200)
    try:
        yield widget
    finally:
        widget.close()
        widget.deleteLater()
        registry.set_backend(previous)
        DocumentManager.instance().close_document(document.uid)


def test_the_copy_of_the_canvas_is_timed_apart_from_the_draw(painted_viewport):
    painted_viewport.grab()  # one real paint through paintEvent
    telemetry = painted_viewport.get_viewport_telemetry()
    assert telemetry["qt_acquire_image_ms"] >= SLOW_COPY_S * 1000.0 * 0.8
    assert telemetry["qt_draw_image_ms"] < telemetry["qt_acquire_image_ms"]


def test_the_parts_never_add_up_to_more_than_the_whole_paint(painted_viewport):
    painted_viewport.grab()
    telemetry = painted_viewport.get_viewport_telemetry()
    parts = telemetry["qt_acquire_image_ms"] + telemetry["qt_draw_image_ms"] + telemetry["qt_cursor_ms"]
    assert 0.0 < parts <= telemetry["qt_paint_total_ms"]


def test_a_paint_without_an_image_does_not_inherit_the_previous_times(painted_viewport):
    painted_viewport.grab()
    EngineRegistry.instance().set_backend(None)
    painted_viewport.grab()
    telemetry = painted_viewport.get_viewport_telemetry()
    assert telemetry["qt_acquire_image_ms"] == 0.0
    assert telemetry["qt_draw_image_ms"] == 0.0


def test_the_presentation_cost_is_the_copy_plus_the_draw():
    assert presentation_ms({"qt_acquire_image_ms": 34.0, "qt_draw_image_ms": 1.5}) == pytest.approx(35.5)
    assert presentation_ms({}) == 0.0  # a viewport that never painted


def test_the_blit_meter_shows_the_copy_and_flags_it_when_it_is_the_bottleneck():
    vp = {"qt_acquire_image_ms": 34.0, "qt_draw_image_ms": 1.5, "qt_paint_total_ms": 40.0}
    reading = {r.key: r for r in read_meters(TelemetrySnapshot(), vp, {"raw_pressure": 0.0})}["blt"]
    assert reading.value == "35.50 ms"
    assert reading.level == "critical"  # 35 ms is over the 16.6 ms frame, though drawImage alone was 1.5
    assert "34.00" in reading.detail and "40.00" in reading.detail


def test_the_tracker_counts_the_copy_in_the_blit_peak():
    tracker = TelemetryTracker()
    tracker.update(TelemetrySnapshot(), {"qt_acquire_image_ms": 34.0, "qt_draw_image_ms": 1.5})
    assert tracker.peaks["blit_ms"] == pytest.approx(35.5)


def test_the_meter_list_keeps_its_twenty_cards():
    """The grid is 4 x 5; the fix changed what meter 6 measures, it did not add a card."""
    assert len(METERS) == 20
