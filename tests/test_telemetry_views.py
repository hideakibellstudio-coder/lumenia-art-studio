"""
Telas de telemetria como views do TelemetryTracker
==================================================
Cockpit em grade, painel e diálogo de diagnóstico leem estado, picos,
histórico e relatório de um lugar só (`TelemetryTracker`); os 20 medidores
são definidos uma vez (`telemetry_meters`). Até 2026-09-24 o cockpit tinha a
própria cópia do estado e um segundo gerador de relatório.
"""
from __future__ import annotations

import pytest
from PySide6 import QtWidgets

from ui.core.dialogs.telemetry_common import banner_style
from ui.core.dialogs.telemetry_grid_window import (
    GridMetricCard as ReExportedGridMetricCard,
    TelemetryGridWindow,
)
from ui.core.dialogs.telemetry_state_history_dialog import TelemetryStateHistoryDialog
from ui.core.engine.telemetry_dto import TelemetrySnapshot
from ui.core.engine.telemetry_meters import METERS, TITLES, read_meters
from ui.core.engine.telemetry_tracker import TelemetryTracker, diagnose
from ui.core.widgets.metric_card import GridMetricCard


@pytest.fixture
def tracker():
    tracker = TelemetryTracker.instance()
    tracker.reset()
    yield tracker
    tracker.reset()


def test_grid_metric_card_contract(qapp):
    card = GridMetricCard(title="Latência", initial_val="1.5 µs", subtitle="Tempo nativo",
                          tag_color="#38bdf8", show_bar=True, bar_max=100)
    assert card.get_info() == ("LATÊNCIA", "1.5 µs", "Tempo nativo")
    card.set_value("2.8 ms", "Alerta de pico", bar_val=75, color="#f87171")
    assert (card.value, card.subtitle, card.bar.value()) == ("2.8 ms", "Alerta de pico", 75)
    assert ReExportedGridMetricCard is GridMetricCard


@pytest.mark.parametrize("dab, und, cmp, blit, key", [
    (500, 200, 300, 2.0, "PIPELINE_EQUILIBRADO"),
    (500, 200, 300, 18.5, "GARGALO_BLIT"),
    (16000, 200, 300, 5.0, "GARGALO_RASTER"),
    (1000, 12000, 300, 5.0, "GARGALO_UNDO"),
    (1000, 200, 11000, 5.0, "GARGALO_COMPOSITOR"),
])
def test_diagnose_classifica_o_gargalo(dab, und, cmp, blit, key):
    _text, state_key, cause = diagnose(dab, und, cmp, blit)
    assert state_key == key and cause
    assert banner_style(state_key).startswith("background-color: rgba(")


def test_meters_um_por_card_e_por_linha_do_relatorio(tracker):
    assert len(METERS) == 20 and len({key for key, _t, _d in METERS}) == 20
    readings = read_meters(TelemetrySnapshot(), {}, tracker.last_active_pen)
    assert [r.key for r in readings] == [key for key, _t, _d in METERS]


def test_meters_mostram_o_ultimo_traco_quando_a_caneta_solta(tracker):
    tracker.update(TelemetrySnapshot(raw_pressure=0.6, dynamic_pressure=0.5, stroke_velocity=420.0), {})
    readings = {r.key: r for r in read_meters(TelemetrySnapshot(), {}, tracker.last_active_pen)}
    assert readings["press"].value == "60 %" and "último traço" in readings["press"].detail
    assert readings["vel"].bar == 420


def test_meters_nivel_dos_gargalos():
    snap = TelemetrySnapshot(time_raster_dab_us=20000.0)
    readings = {r.key: r for r in read_meters(snap, {"qt_fps": 20.0, "qt_draw_image_ms": 12.0}, {"raw_pressure": 0.0})}
    assert readings["dab"].level == "critical"
    assert readings["fps"].level == "critical"
    assert readings["blt"].level == "warning"


def test_meters_simd_vem_do_motor():
    on = {r.key: r for r in read_meters(TelemetrySnapshot(simd_active=True), {}, {"raw_pressure": 0.0})}
    off = {r.key: r for r in read_meters(TelemetrySnapshot(simd_active=False), {}, {"raw_pressure": 0.0})}
    assert "AVX2 (vetorizado)" == on["hw"].value
    assert "Escalar" in off["hw"].value


def test_state_history_dialog(qapp):
    counts = {"PIPELINE_EQUILIBRADO": 5, "GARGALO_RASTER": 1}
    history = [
        {"time": "12:00:00.123", "to_state": "Equilibrado", "cause": "Normal"},
        {"time": "12:01:00.456", "to_state": "Raster", "cause": "Pincel gigante"},
    ]
    dlg = TelemetryStateHistoryDialog(counts, history)
    assert dlg.windowTitle() == "Histórico de Alterações de Estado do Pipeline"
    text = dlg.findChild(QtWidgets.QPlainTextEdit).toPlainText()
    assert text.index("Raster") < text.index("Equilibrado")  # mais recente primeiro


def test_cockpit_mostra_o_estado_do_tracker(qapp, tracker):
    win = TelemetryGridWindow()
    try:
        assert list(win.cards) == [key for key, _t, _d in METERS]
        assert "PIPELINE EQUILIBRADO" in win.lbl_bottleneck.text()

        snap = TelemetrySnapshot(time_raster_dab_us=23574.7, time_undo_record_us=5.2, time_composite_us=1112.3)
        tracker.update(snap, {"qt_draw_image_ms": 0.15})
        win.show_readings(snap, {"qt_draw_image_ms": 0.15})
        assert tracker.current_state_key == "GARGALO_RASTER"
        assert "GARGALO EM RASTER" in win.lbl_bottleneck.text()
        assert tracker.state_counts["GARGALO_RASTER"] == 1
        assert win.cards["dab"].value == "23574.7 µs"

        calm = TelemetrySnapshot(time_raster_dab_us=850.0)
        tracker.update(calm, {"qt_draw_image_ms": 0.15})
        win.show_readings(calm, {"qt_draw_image_ms": 0.15})
        assert "PIPELINE EQUILIBRADO" in win.lbl_bottleneck.text()
        assert tracker.transition_count >= 3

        report = win.generate_full_report()
        for heading in ("COCKPIT DE TELEMETRIA & DIAGNÓSTICO EM GRID",
                        "DIAGNÓSTICO DO PIPELINE & ALTERAÇÕES DE ESTADO", "GARGALO EM RASTER",
                        "Picos Máximos de Estresse Registrados na Sessão:",
                        "PAINEL COMPLETO EM GRID (TODOS OS 20 MEDIDORES EM TEMPO REAL)",
                        "Fixação Sempre no Topo  : SIM"):
            assert heading in report
        for title in TITLES.values():  # os 20 medidores do cockpit estão no relatório
            assert title.upper() in report

        win.reset_metrics()
        assert tracker.current_state_key == "PIPELINE_EQUILIBRADO"
        assert tracker.state_counts["GARGALO_RASTER"] == 0
    finally:
        win.close()


def test_cockpit_fixar_no_topo_entra_no_relatorio(qapp, tracker):
    win = TelemetryGridWindow()
    try:
        assert win.stay_on_top
        win.toggle_pin()
        assert not win.stay_on_top
        assert "Fixação Sempre no Topo  : NÃO" in win.generate_full_report()
    finally:
        win.close()
