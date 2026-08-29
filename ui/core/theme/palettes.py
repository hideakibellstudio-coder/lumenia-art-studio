DARK_PALETTE = {
    "bg_main": "#0f172a",       # Slate 900
    "bg_panel": "#1e293b",      # Slate 800
    "border": "#334155",        # Slate 700
    "border_control": "#475569",# Slate 600
    "text_main": "#f8fafc",     # Slate 50
    "text_sec": "#94a3b8",      # Slate 400
    "accent": "#3b82f6",        # Blue 500
    "accent_hover": "#60a5fa",  # Blue 400
    "accent_bg": "#1e3a8a",     # Blue 900 (transparente)
    "slider_groove": "#1e293b",
    "slider_handle": "#3b82f6"
}

LIGHT_PALETTE = {
    "bg_main": "#f8fafc",       # Slate 50
    "bg_panel": "#ffffff",      # Puro branco
    "border": "#e2e8f0",        # Slate 200
    "border_control": "#cbd5e1",# Slate 300
    "text_main": "#0f172a",     # Slate 900
    "text_sec": "#64748b",      # Slate 500
    "accent": "#2563eb",        # Blue 600
    "accent_hover": "#3b82f6",  # Blue 500
    "accent_bg": "#dbeafe",     # Blue 100
    "slider_groove": "#e2e8f0",
    "slider_handle": "#2563eb"
}


QSS_TEMPLATE = """
QMainWindow, QDialog {{
    background-color: {bg_main};
    color: {text_main};
}}

QWidget {{
    color: {text_main};
    font-family: "Segoe UI", "Inter", sans-serif;
}}

QMenuBar {{
    background-color: {bg_panel};
    border-bottom: 1px solid {border};
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 6px 12px;
}}

QMenuBar::item:selected {{
    background-color: {accent_bg};
    border-radius: 4px;
}}

QMenu {{
    background-color: {bg_panel};
    color: {text_main};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 4px;
}}

QMenu::item {{
    background-color: transparent;
    padding: 7px 28px 7px 34px;
    margin: 2px 4px;
    border-radius: 4px;
    font-size: 12px;
}}

QMenu::item:selected {{
    background-color: {accent};
    color: #ffffff;
}}

QMenu::item:disabled {{
    color: {text_muted};
    background-color: transparent;
}}

QMenu::icon {{
    padding-left: 10px;
}}

QMenu::separator {{
    height: 1px;
    background-color: {border};
    margin: 5px 8px;
}}

QStatusBar {{
    background-color: {bg_panel};
    border-top: 1px solid {border};
    color: {text_sec};
    font-size: 11px;
}}

QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
    border: none;
    color: {text_main};
}}

QDockWidget::title {{
    background-color: {bg_panel};
    padding: 8px;
    border-bottom: 1px solid {border};
    font-weight: bold;
}}

QGroupBox {{
    background-color: {bg_panel};
    border: 1px solid {border};
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    padding: 16px 8px 8px 8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {accent};
    background-color: {bg_panel};
}}

QPushButton {{
    background-color: {bg_main};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    min-height: 18px;
}}

QPushButton:hover {{
    border-color: {accent};
    background-color: {accent_bg};
}}

QPushButton:pressed {{
    background-color: {accent};
    color: #ffffff;
}}

QSlider::groove:horizontal {{
    border: 1px solid {border};
    height: 6px;
    background: {slider_groove};
    margin: 2px 0;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {slider_handle};
    border: none;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}}

QSlider::handle:horizontal:hover {{
    background: {accent_hover};
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border_control};
    border-radius: 4px;
    background-color: {bg_main};
}}

QCheckBox::indicator:unchecked:hover {{
    border-color: {accent};
}}

QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}

QRadioButton {{
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border_control};
    border-radius: 4px;
    background-color: {bg_main};
}}

QRadioButton::indicator:unchecked:hover {{
    border-color: {accent};
}}

QRadioButton::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
    border-radius: 4px;
}}

QLabel {{
    color: {text_main};
}}

QToolBar {{
    background-color: {bg_panel};
    border-bottom: 1px solid {border};
    border-top: none;
    border-left: none;
    border-right: none;
    spacing: 6px;
    padding: 4px;
}}

QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px;
}}

QToolButton:hover {{
    background-color: {accent_bg};
    border: 1px solid {border};
}}

QToolButton:pressed {{
    background-color: {accent};
}}

QToolButton:checked {{
    background-color: {accent_bg};
    border: 1px solid {accent};
}}
"""
