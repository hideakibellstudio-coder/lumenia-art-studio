"""
TelemetryPanelTheme — Estilização e Temas do Painel de Telemetria
==================================================================
Aplica folhas de estilo nos widgets, barras de progresso e botões do TelemetryPanel.
"""

from __future__ import annotations
from typing import Any
from ui.core.theme.manager import ThemeManager


def apply_telemetry_panel_theme(panel: Any) -> None:
    tm = ThemeManager.instance()
    border = tm.get_color("border")
    muted = tm.get_color("text_sec")
    accent = tm.get_color("accent")
    text = tm.get_color("text_main")
    bg_card = tm.get_color("bg_card")

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
            background-color: rgba(0, 0, 0, 0.3);
            border: 1px solid {border};
            border-radius: 3px;
        }}
        QProgressBar::chunk {{
            background-color: {accent};
            border-radius: 2px;
        }}
        QPushButton#BtnOpenGrid {{
            background-color: rgba(56, 189, 248, 0.15);
            border: 1px solid #38bdf8;
            border-radius: 4px;
            color: #38bdf8;
            font-weight: bold;
            font-size: 11px;
        }}
        QPushButton#BtnOpenGrid:hover {{
            background-color: rgba(56, 189, 248, 0.3);
            border-color: #7dd3fc;
            color: #ffffff;
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
