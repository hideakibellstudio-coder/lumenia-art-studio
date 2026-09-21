"""
ThemeDialogStyles — Folhas de Estilo e Formatação Visual do Diálogo de Temas
=============================================================================
Aplica tokens de cor e estilização CSS nos componentes de ThemeDialog.
"""

from __future__ import annotations
from typing import Any


def apply_theme_dialog_styles(dialog: Any, theme_manager: Any) -> None:
    tm = theme_manager
    bg_app = tm.get_color("bg_main")
    bg_panel = tm.get_color("bg_panel")
    border = tm.get_color("border")
    border_muted = tm.get_color("border_muted")
    text_main = tm.get_color("text_main")
    text_sec = tm.get_color("text_sec")
    accent = tm.get_color("accent")
    accent_hover = tm.get_color("accent_hover")
    bg_card = tm.get_color("bg_card")

    dialog.setStyleSheet(f"""
        QDialog#ThemeDialog {{
            background-color: {bg_app};
            color: {text_main};
        }}
        QGroupBox {{
            font-size: 11px;
            font-weight: bold;
            color: {text_sec};
            border: 1px solid {border};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 14px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }}
        QLineEdit, QComboBox {{
            background-color: {bg_card};
            color: {text_main};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {bg_card};
            color: {text_main};
            selection-background-color: {accent};
            selection-color: {text_main};
            border: 1px solid {border};
        }}
        QPushButton {{
            background-color: {bg_card};
            color: {text_main};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 6px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {accent};
            color: {text_main};
        }}
        QPushButton:disabled {{
            background-color: {bg_panel};
            color: {text_sec};
            border-color: {border_muted};
        }}
    """)
    dialog.btn_apply.setStyleSheet(f"""
        QPushButton {{
            background-color: {accent};
            color: {text_main};
            border: none;
            border-radius: 6px;
            font-weight: bold;
            padding: 6px 16px;
        }}
        QPushButton:hover {{
            background-color: {accent_hover};
        }}
        QPushButton:disabled {{
            background-color: {bg_panel};
            color: {text_sec};
            border: 1px solid {border_muted};
        }}
    """)
