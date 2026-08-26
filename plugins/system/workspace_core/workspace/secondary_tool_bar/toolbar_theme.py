"""Theme styling for Secondary Toolbar."""

from ui.core.theme.manager import ThemeManager

def apply_secondary_toolbar_theme(container):
    theme = ThemeManager.instance()
    bg_panel = theme.get_color("bg_panel") or "#1f1f23"
    border = theme.get_color("border") or "#3f3f46"
    text_main = theme.get_color("text_main") or "#ffffff"
    accent = theme.get_color("accent") or "#3b82f6"

    container.setStyleSheet(f"""
        #SecondaryBarContainer {{
            background-color: {bg_panel};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        QLabel {{
            color: {text_main};
            font-size: 11px;
            qproperty-alignment: 'AlignVCenter | AlignLeft';
        }}
        QComboBox, QFontComboBox, QSpinBox {{
            background-color: rgba(255,255,255,0.06);
            color: {text_main};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 0px 6px;
            font-size: 11px;
            min-height: 24px;
            max-height: 24px;
        }}
        QComboBox:hover, QFontComboBox:hover, QSpinBox:hover {{
            border-color: {accent};
        }}
        QToolButton, QPushButton {{
            background-color: rgba(255,255,255,0.06);
            color: {text_main};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 0px 8px;
            font-size: 11px;
            min-height: 24px;
            max-height: 24px;
        }}
        QToolButton:hover, QPushButton:hover {{
            border-color: {accent};
            background-color: rgba(255,255,255,0.12);
        }}
        QToolButton:checked {{
            background-color: {accent};
            color: #ffffff;
            border: 1px solid {accent};
        }}
        QSlider::groove:horizontal {{
            height: 4px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {accent};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {accent};
            border: 1px solid #ffffff;
            width: 12px;
            margin-top: -4px;
            margin-bottom: -4px;
            border-radius: 6px;
        }}
    """)
