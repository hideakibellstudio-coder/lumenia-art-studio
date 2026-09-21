"""
TelemetryPanelTheme — Estilização e Temas do Painel de Telemetria
==================================================================
Aplica folhas de estilo nos widgets, barras de progresso e botões do TelemetryPanel.
"""

from __future__ import annotations
from typing import Any
from PySide6 import QtGui
from ui.core.theme.manager import ThemeManager


def apply_telemetry_panel_theme(panel: Any) -> None:
    tm = ThemeManager.instance()
    border = tm.get_color("border")
    muted = tm.get_color("text_sec")
    accent = tm.get_color("accent")
    text = tm.get_color("text_main")
    bg_card = tm.get_color("bg_card")
    stage_kin = tm.get_color("TELEMETRY_STAGE_KINEMATICS", "#38bdf8")
    stage_kin_hover = QtGui.QColor(stage_kin).lighter(130).name()
    _sk_c = QtGui.QColor(stage_kin)
    stage_kin_bg = f"rgba({_sk_c.red()}, {_sk_c.green()}, {_sk_c.blue()}, 0.15)"
    stage_kin_bg_hover = f"rgba({_sk_c.red()}, {_sk_c.green()}, {_sk_c.blue()}, 0.3)"
    fg_on_accent = tm.get_color("FG_PRIMARY", "#ffffff")
    track_shadow = tm.get_color("SHADOW", "rgba(0, 0, 0, 0.3)")

    panel.setStyleSheet(f"""
        QLabel#TelemLabel {{
            color: {muted};
            font-size: 9px;
            font-weight: bold;
            letter-spacing: 0.5px;
        }}
        QLabel#TelemStatus {{
            font-size: 10px;
            color: {muted};
        }}
        QProgressBar {{
            background-color: {track_shadow};
            border: 1px solid {border};
            border-radius: 3px;
        }}
        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 2px;
        }}
        QPushButton#BtnOpenGrid {{
            background-color: {stage_kin_bg};
            border: 1px solid {stage_kin};
            border-radius: 4px;
            color: {stage_kin};
            font-weight: bold;
            font-size: 11px;
        }}
        QPushButton#BtnOpenGrid:hover {{
            background-color: {stage_kin_bg_hover};
            border-color: {stage_kin_hover};
            color: {fg_on_accent};
        }}
        QPushButton#BtnToggleTelemetry {{
            background-color: {bg_card};
            border: 1px solid {border};
            border-radius: 4px;
            color: {text};
            font-weight: bold;
            font-size: 10px;
        }}
        QPushButton#BtnToggleTelemetry:hover {{
            border-color: {accent};
        }}
        QPushButton#BtnOpenDialog {{
            background-color: transparent;
            border: 1px solid {border};
            border-radius: 4px;
            color: {text};
            font-size: 10px;
        }}
        QPushButton#BtnOpenDialog:hover {{
            background-color: {bg_card};
            border-color: {accent};
        }}
        QLabel {{
            color: {text};
        }}
    """)
