"""
TelemetryStateHistoryDialog — linha do tempo das transições de estado do pipeline.
==================================================================================
Mostra as contagens e o histórico do `TelemetryTracker` (clique no banner do
cockpit). Até 2026-09-24 este arquivo (`telemetry_grid_report.py`) tinha
também um segundo gerador do relatório e do diagnóstico, que lia os atributos
privados da janela; hoje os dois estão em `ui/core/engine/`
(`telemetry_report.py` e `telemetry_tracker.diagnose`).
"""

from __future__ import annotations

from typing import Dict, List
from PySide6 import QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.icons import get_icon


class TelemetryStateHistoryDialog(BaseFramelessDialog):
    """Diálogo modal para inspeção do histórico cronológico de transições de estado e gargalos."""

    def __init__(
        self,
        state_counts: Dict[str, int],
        state_history: List[Dict[str, str]],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        title = "Histórico de Alterações de Estado do Pipeline"
        super().__init__(title=title, icon_name="chart", parent=parent, modal=True)
        self.setWindowTitle(title)
        tm = ThemeManager.instance()
        self.resize(680, 420)

        dlg_lo = self.content_layout
        dlg_lo.setSpacing(10)

        lbl_hdr = QtWidgets.QLabel("<b>Linha do Tempo de Alterações de Estado (Gargalos vs Equilíbrio)</b>")
        lbl_hdr.setStyleSheet(f"font-size: 13px; color: {tm.get_color('TELEMETRY_STAGE_KINEMATICS', '#38bdf8')};")
        dlg_lo.addWidget(lbl_hdr)

        summary_text = (
            f"Equilibrado: {state_counts.get('PIPELINE_EQUILIBRADO', 0)}x | "
            f"Raster (>15ms): {state_counts.get('GARGALO_RASTER', 0)}x | "
            f"Blit (>16ms): {state_counts.get('GARGALO_BLIT', 0)}x | "
            f"Undo (>10ms): {state_counts.get('GARGALO_UNDO', 0)}x | "
            f"Compositor (>10ms): {state_counts.get('GARGALO_COMPOSITOR', 0)}x"
        )
        lbl_sum = QtWidgets.QLabel(summary_text)
        lbl_sum.setStyleSheet(f"font-size: 11px; color: {tm.get_color('FG_SECONDARY', '#9ca3af')};")
        dlg_lo.addWidget(lbl_sum)

        txt_history = QtWidgets.QPlainTextEdit()
        txt_history.setReadOnly(True)
        txt_history.setStyleSheet(
            f"font-family: monospace; font-size: 11px; background-color: {tm.get_color('BG_DARKEST', '#111827')}; "
            f"color: {tm.get_color('FG_PRIMARY', '#f3f4f6')}; border: 1px solid {tm.get_color('BORDER', '#374151')};"
        )

        hist_lines = []
        for t in reversed(state_history):
            hist_lines.append(f"[{t['time']}] {t['to_state']}\n  └─ Motivo: {t['cause']}\n")
        txt_history.setPlainText("\n".join(hist_lines) if hist_lines else "Nenhuma alteração registrada.")
        dlg_lo.addWidget(txt_history, 1)

        btn_row = QtWidgets.QHBoxLayout()
        btn_copy_hist = QtWidgets.QPushButton(" Copiar Histórico")
        btn_copy_hist.setIcon(get_icon("copy", tm.get_color("text_main")))
        btn_copy_hist.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(txt_history.toPlainText()))
        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_copy_hist)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        dlg_lo.addLayout(btn_row)
