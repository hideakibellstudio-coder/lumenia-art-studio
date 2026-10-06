"""A calibração da caneta no app: configuração, backend por documento, menu e diálogo.

O motor aplica a curva (tests/test_pen_pressure_calibration.py mede isso); aqui se mede o
caminho do artista até lá:

  1. a configuração salva só aceita números sãos e um arquivo estragado volta à identidade;
  2. a curva escolhida vale para todos os documentos, os abertos e os que ainda vão abrir;
  3. o quadro do diálogo mede a pressão bruta da caneta e o assistente sugere o aperto habitual;
  4. Aplicar grava no motor e na configuração; "Restaurar padrão" volta à identidade;
  5. o menu Configurações tem a ação e a repassa.
"""

from __future__ import annotations

import pytest
from PySide6 import QtCore, QtGui

from ui.core.state.pen_calibration import MIN_MEASURED_SAMPLES, PenCalibration
from ui.infrastructure.config.manager import ConfigManager
from ui.infrastructure.config.schema import migrate_config, normalize_section

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)


# ── 1. Configuração ─────────────────────────────────────────────────────────

def test_the_pen_section_keeps_sane_numbers_as_floats():
    assert normalize_section("pen", {"floor": 0, "ceiling": 1, "gamma": 1}) == {"floor": 0.0, "ceiling": 1.0, "gamma": 1.0}


@pytest.mark.parametrize("key,value", [("floor", -0.1), ("ceiling", 1.5), ("gamma", 0.0), ("gamma", 9.0),
                                       ("ceiling", float("nan")), ("floor", "abc"), ("gamma", True)])
def test_the_pen_section_rejects_values_the_engine_would_have_to_repair(key, value):
    with pytest.raises(ValueError):
        normalize_section("pen", {key: value})


def test_a_damaged_pen_section_loses_only_its_bad_keys():
    migrated = migrate_config({"schema_version": 1, "pen": {"floor": 0.05, "ceiling": "x", "gamma": 0.8}})
    assert migrated["pen"] == {"floor": 0.05, "gamma": 0.8}
    assert PenCalibration.from_config(migrated["pen"]) == PenCalibration(0.05, 1.0, 0.8)


def test_the_factory_default_is_the_identity():
    from ui.infrastructure.config.manager import DEFAULT_CONFIG
    assert PenCalibration.from_config(DEFAULT_CONFIG["pen"]).is_identity


# ── 2. Backend: vale para todos os documentos ───────────────────────────────

def _backend():
    from ui.infrastructure.bridge_client.aladyn import AladynBackend
    return AladynBackend()


def test_the_curve_reaches_open_documents_and_documents_opened_later():
    backend = _backend()
    backend.set_active_document_context("pen_a", 64, 64)
    try:
        assert backend.get_pressure_calibration() == (0.0, 1.0, 1.0)
        backend.set_pressure_calibration(0.05, 0.35, 0.8)
        backend.set_active_document_context("pen_b", 64, 64)  # nasce depois da calibração
        assert backend.get_pressure_calibration() == pytest.approx((0.05, 0.35, 0.8))
        backend.set_active_document_context("pen_a", 64, 64)  # já existia antes dela
        assert backend.get_pressure_calibration() == pytest.approx((0.05, 0.35, 0.8))
    finally:
        backend.close_document_context("pen_a")
        backend.close_document_context("pen_b")


def test_the_curve_changes_what_a_weak_pen_paints():
    """Pelo caminho do app (`start_stroke`/`paint_stroke`): pressão de 0,3 pinta como 1,0 quando 0,3 é o teto."""
    def ink_on_white(ceiling: float) -> int:
        backend = _backend()
        backend.set_active_document_context("pen_stroke", 120, 40)
        try:
            backend.set_engine_type(1)  # lápis: a pressão decide a deposição
            backend.set_brush_size(10.0)
            backend.set_pressure_calibration(0.0, ceiling, 1.0)
            backend.start_stroke(10.0, 20.0, 0.3, 1.0)
            for i in range(1, 30):
                backend.paint_stroke(10.0 + i * 3.0, 20.0, 0.3, 1.0 + 0.008 * i)
            backend.end_stroke()
            import numpy as np
            pixels = np.frombuffer(backend.get_display_pixel_buffer(), dtype=np.uint8).reshape((40, 120, 4))
            return int((255 - pixels[:, :, 0].astype(int)).sum())  # tinta preta sobre o fundo branco
        finally:
            backend.close_document_context("pen_stroke")

    weak_calibrated, weak_raw = ink_on_white(0.3), ink_on_white(1.0)
    assert weak_raw > 0
    assert weak_calibrated > 1.2 * weak_raw, (
        f"a calibração não reforçou o traço da caneta fraca ({weak_calibrated} contra {weak_raw})"
    )


# ── 3 e 4. O diálogo ────────────────────────────────────────────────────────

class _Backend:
    """O mínimo que o diálogo pede ao motor, registrando o que recebe."""

    def __init__(self, calibration=(0.0, 1.0, 1.0)):
        self.calibration = calibration

    def get_pressure_calibration(self):
        return self.calibration

    def set_pressure_calibration(self, floor, ceiling, gamma):
        self.calibration = (floor, ceiling, gamma)


def _dialog(qapp, backend):
    from ui.core.dialogs.pen_calibration_dialog import PenCalibrationDialog
    return PenCalibrationDialog(lambda: backend)


def _draw(dialog, count, pressure=0.25):
    for i in range(count):
        dialog.pad.feed(pressure + 0.05 * ((i % 5) - 2) / 2)


def test_the_dialog_opens_on_the_stored_curve(qapp):
    dialog = _dialog(qapp, _Backend((0.05, 0.4, 0.8)))
    assert dialog.chosen_calibration() == PenCalibration(0.05, 0.4, 0.8)


def test_the_assistant_waits_for_enough_samples_then_suggests_the_usual_pressure(qapp):
    dialog = _dialog(qapp, _Backend())
    assert not dialog.btn_suggest.isEnabled()
    _draw(dialog, MIN_MEASURED_SAMPLES - 1)
    assert not dialog.btn_suggest.isEnabled(), "poucas amostras não devem gerar sugestão"
    _draw(dialog, 10)
    assert dialog.btn_suggest.isEnabled()
    dialog.btn_suggest.click()
    assert 0.2 <= dialog.chosen_calibration().ceiling <= 0.35


def test_a_pen_that_already_covers_the_range_gets_no_suggestion(qapp):
    dialog = _dialog(qapp, _Backend())
    _draw(dialog, MIN_MEASURED_SAMPLES + 20, pressure=0.97)
    assert not dialog.btn_suggest.isEnabled()
    assert dialog.chosen_calibration().is_identity


def test_clearing_the_measurement_forgets_the_samples(qapp):
    dialog = _dialog(qapp, _Backend())
    _draw(dialog, MIN_MEASURED_SAMPLES + 10)
    dialog.btn_clear.click()
    assert dialog.pad.samples == [] and not dialog.btn_suggest.isEnabled()


def test_apply_writes_to_the_engine_and_to_the_saved_settings(qapp):
    backend = _Backend()
    dialog = _dialog(qapp, backend)
    applied = []
    dialog.calibrationApplied.connect(lambda: applied.append(True))
    dialog.spin_floor.setValue(5)
    dialog.spin_ceiling.setValue(35)
    dialog.spin_gamma.setValue(0.8)
    dialog.btn_apply.click()
    assert backend.calibration == pytest.approx((0.05, 0.35, 0.8))
    assert PenCalibration.from_config(ConfigManager.instance().get_section("pen")) == PenCalibration(0.05, 0.35, 0.8)
    assert applied == [True]


def test_restore_default_goes_back_to_the_identity(qapp):
    dialog = _dialog(qapp, _Backend((0.05, 0.4, 0.8)))
    dialog.btn_reset.click()
    assert dialog.chosen_calibration().is_identity


def test_the_dialog_survives_a_missing_engine(qapp):
    from ui.core.dialogs.pen_calibration_dialog import PenCalibrationDialog
    dialog = PenCalibrationDialog(lambda: None)
    dialog.spin_ceiling.setValue(40)
    dialog.btn_apply.click()
    assert PenCalibration.from_config(ConfigManager.instance().get_section("pen")).ceiling == pytest.approx(0.4)


# ── O quadro: pressão bruta da caneta, nunca a do mouse ──────────────────────

def _tablet_event(kind, x, y, pressure):
    device = QtGui.QPointingDevice.primaryPointingDevice()
    point = QtCore.QPointF(x, y)
    return QtGui.QTabletEvent(kind, device, point, point, pressure, 0.0, 0.0, 0.0, 0.0, 0.0,
                              QtCore.Qt.NoModifier, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton)


def test_the_pad_collects_the_pressure_of_pen_moves_only(qapp):
    from ui.core.dialogs.pen_calibration_pad import PressurePad
    pad = PressurePad()
    pad.resize(300, 200)
    pad.tabletEvent(_tablet_event(QtCore.QEvent.TabletMove, 10, 10, 0.5))  # sem pouso: não conta
    pad.tabletEvent(_tablet_event(QtCore.QEvent.TabletPress, 10, 10, 0.1))
    pad.tabletEvent(_tablet_event(QtCore.QEvent.TabletMove, 20, 10, 0.3))
    pad.tabletEvent(_tablet_event(QtCore.QEvent.TabletMove, 30, 10, 0.2))
    pad.tabletEvent(_tablet_event(QtCore.QEvent.TabletRelease, 30, 10, 0.0))
    assert pad.samples == pytest.approx([0.3, 0.2])
    pad.grab()  # desenhar o rastro não pode falhar


# ── 5. Menu ────────────────────────────────────────────────────────────────

def test_the_settings_menu_offers_the_calibration_and_the_bar_forwards_it(qapp):
    from ui.core.components.menu_bar.menu_bar import MenuBar
    bar = MenuBar()
    seen = []
    bar.penCalibrationRequested.connect(lambda: seen.append(True))
    bar.settings_menu.act_pen.trigger()
    assert seen == [True]
