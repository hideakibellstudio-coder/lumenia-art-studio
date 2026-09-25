"""Painel avançado do pincel: seções com estado próprio e dois caminhos claros.

Parâmetro rápido (tamanho, opacidade, estabilizador, contraste, inverter,
espaçamento) vai ao BrushState; avançado (mínimos, ponta, jitter, textura)
vai ao motor pelo BrushEngineWriter. Até 2026-09-24 não havia teste deste
painel; o comportamento foi caracterizado (23 controles) antes e depois da
refatoração e ficou idêntico.
"""
import pytest
from PySide6 import QtCore, QtWidgets

from ui.core.engine.registry import EngineRegistry
from ui.core.plugins.registry import ServiceRegistry
from ui.core.state import BrushParam, install_app_state


@pytest.fixture
def panel(qapp, monkeypatch):
    from ui.infrastructure.bridge_client.aladyn import AladynBackend
    from ui.plugins.panels.brush_plugin.advanced_panel import AdvancedPanel
    backend = AladynBackend()
    backend.set_active_document_context("adv-panel", 32, 32)
    monkeypatch.setattr(EngineRegistry.instance(), "get_backend", lambda: backend)
    state = install_app_state(ServiceRegistry(), lambda: backend)
    widget = AdvancedPanel(state.brush)
    yield widget, state.brush, backend
    widget.deleteLater()
    backend.close_document_context("adv-panel")


def _section(panel, cls_name):
    return next(s for s in panel.sections if type(s).__name__ == cls_name)


def test_quick_param_goes_to_state_and_engine_param_to_engine(panel):
    widget, brush, backend = panel
    sizes = _section(widget, "SizeOpacitySection")
    sizes.slider_opacity.setValue(40)
    assert brush.value(BrushParam.OPACITY) == pytest.approx(0.4)

    jitter = _section(widget, "JittersSection")
    jitter.sl_jit_size.setValue(25)
    assert backend.get_brush_profile_dict()["jitter_size"] == pytest.approx(0.25)
    assert brush.value(BrushParam.OPACITY) == pytest.approx(0.4)


def test_state_and_engine_profile_are_shown(panel):
    widget, brush, backend = panel
    brush.set_value(BrushParam.SPACING, 0.3)
    assert _section(widget, "SpacingSection").slider_spacing.value() == 30

    backend.set_brush_param("tip", "angle", 120.0)
    widget.sync_from_engine_profile()
    assert _section(widget, "TipGeometrySection").sl_angle.value() == 120


def test_widgets_belong_to_sections_not_to_the_panel(panel):
    widget, _brush, _backend = panel
    for name in ("slider_size", "sl_jit_size", "chk_b_grain", "shape_preview"):
        assert name not in vars(widget), f"{name} voltou a ser pendurado no painel"


def test_pin_from_section_reaches_panel_signal(panel):
    widget, _brush, _backend = panel
    pins = []
    widget.pinToggled.connect(lambda name, on: pins.append((name, on)))
    _section(widget, "SpacingSection").slider_spacing.pin_cb.setChecked(True)
    assert pins == [("spacing", True)]


def test_floating_panel_opens_beside_the_canvas_area(qapp):
    from ui.core.dialogs.floating_panel_window import FloatingPanelWindow
    from tests.qt_windows import destroy_now

    host = QtWidgets.QWidget()
    host.resize(200, 100)
    anchor = QtWidgets.QPushButton("abrir", host)
    area = QtCore.QRect(100, 50, 800, 600)
    window = FloatingPanelWindow(lambda: area)
    window.resize(330, 400)
    try:
        window.show_beside_canvas(anchor, min_height=420)
        screen = anchor.screen().availableGeometry()
        on_right = anchor.mapToGlobal(QtCore.QPoint(0, 0)).x() > screen.center().x()
        expected_x = area.x() + area.width() - window.width() - 10 if on_right else area.x() + 10
        assert window.x() == max(screen.left() + 10, min(expected_x, screen.right() - window.width() - 10))
        assert window.height() == min(580, screen.height() - 40)
    finally:
        destroy_now(window, host)
