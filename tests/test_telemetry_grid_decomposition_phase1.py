"""
Testes de Regressão e Contrato para a Decomposição da Fase 1 da Camada 5 (ARCcC v2)
====================================================================================
Valida o desacoplamento de GridMetricCard, TelemetryStateHistoryDialog,
TelemetryReportGenerator e TelemetryGridWindow.
"""

import os
import pytest
from PySide6 import QtWidgets, QtCore

from ui.core.widgets.metric_card import GridMetricCard
from ui.core.dialogs.telemetry_grid_report import (
    TelemetryStateHistoryDialog,
    TelemetryReportGenerator,
)
from ui.core.dialogs.telemetry_grid_window import (
    TelemetryGridWindow,
    GridMetricCard as ReExportedGridMetricCard,
)


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_grid_metric_card_contract(qapp):
    """Valida o funcionamento isolado do componente GridMetricCard."""
    card = GridMetricCard(
        title="Latência",
        initial_val="1.5 µs",
        subtitle="Tempo nativo",
        tag_color="#38bdf8",
        show_bar=True,
        bar_max=100,
    )
    assert card.title == "LATÊNCIA"
    assert card.value == "1.5 µs"
    assert card.subtitle == "Tempo nativo"
    assert card.get_info() == ("LATÊNCIA", "1.5 µs", "Tempo nativo")

    # Atualização dinâmica
    card.set_value("2.8 ms", "Alerta de pico", bar_val=75, color="#f87171")
    assert card.value == "2.8 ms"
    assert card.subtitle == "Alerta de pico"
    assert card.bar is not None
    assert card.bar.value() == 75

    # Re-exportação para retrocompatibilidade
    assert ReExportedGridMetricCard is GridMetricCard


def test_telemetry_report_diagnose_pipeline():
    """Valida a classificação determinística de gargalos operacionais."""
    # 1. Equilibrado
    state, key, style, cause = TelemetryReportGenerator.diagnose_pipeline(500, 200, 300, 2.0)
    assert key == "PIPELINE_EQUILIBRADO"
    assert "EQUILIBRADO" in state

    # 2. Blit Lento (> 16.6ms)
    state, key, style, cause = TelemetryReportGenerator.diagnose_pipeline(500, 200, 300, 18.5)
    assert key == "GARGALO_BLIT"

    # 3. Raster Crítico (> 15000us)
    state, key, style, cause = TelemetryReportGenerator.diagnose_pipeline(16000, 200, 300, 5.0)
    assert key == "GARGALO_RASTER"

    # 4. Undo Lento (> 10000us)
    state, key, style, cause = TelemetryReportGenerator.diagnose_pipeline(1000, 12000, 300, 5.0)
    assert key == "GARGALO_UNDO"

    # 5. Compositor Lento (> 10000us)
    state, key, style, cause = TelemetryReportGenerator.diagnose_pipeline(1000, 200, 11000, 5.0)
    assert key == "GARGALO_COMPOSITOR"


def test_telemetry_state_history_dialog_instantiation(qapp):
    """Valida a construção correta do diálogo de histórico de transições."""
    counts = {"PIPELINE_EQUILIBRADO": 5, "GARGALO_RASTER": 1}
    history = [
        {"time": "12:00:00.123", "to_state": "Equilibrado", "cause": "Normal"},
        {"time": "12:01:00.456", "to_state": "Raster", "cause": "Pincel gigante"},
    ]
    dlg = TelemetryStateHistoryDialog(counts, history)
    assert dlg.windowTitle() == "Histórico de Alterações de Estado do Pipeline"
    assert dlg.findChildren(QtWidgets.QPlainTextEdit) is not None


def test_telemetry_grid_window_composition(qapp):
    """Valida a instanciação do TelemetryGridWindow e a presença dos 20 medidores."""
    win = TelemetryGridWindow()
    try:
        assert len(win._cards) == 20
        assert hasattr(win, "c_kin")
        assert hasattr(win, "c_int")
        assert hasattr(win, "c_dab")
        assert hasattr(win, "c_und")
        assert hasattr(win, "c_cmp")
        assert hasattr(win, "c_blt")
        assert hasattr(win, "c_lat")
        assert hasattr(win, "c_fps")
        assert hasattr(win, "c_hz")
        assert hasattr(win, "c_dabs_sec")
        assert hasattr(win, "c_dabs")
        assert hasattr(win, "c_dirty")
        assert hasattr(win, "c_area")
        assert hasattr(win, "c_tiles")
        assert hasattr(win, "c_ram_canvas")
        assert hasattr(win, "c_ram_undo")
        assert hasattr(win, "c_press")
        assert hasattr(win, "c_vel")
        assert hasattr(win, "c_lag")
        assert hasattr(win, "c_hw")

        # Teste de geração de relatório textual
        report = win.generate_full_report()
        assert "LUMENIA ART STUDIO — COCKPIT DE TELEMETRIA" in report
        assert "DIAGNÓSTICO DO PIPELINE" in report
    finally:
        win.close()
