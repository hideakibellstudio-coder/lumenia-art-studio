"""Theme styling for Advanced Panel."""

from ui.core.theme.manager import ThemeManager

def get_advanced_panel_qss() -> str:
    tm     = ThemeManager.instance()
    bg     = tm.get_color("bg_main")
    bg2    = tm.get_color("bg_panel")
    text   = tm.get_color("text_main")
    muted  = tm.get_color("text_sec")
    accent = tm.get_color("accent")
    border = tm.get_color("border")

    return f"""
        AdvancedPanel {{
            background: transparent;
        }}
        #AdvContainer {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        #AdvTitleBar {{
            background: {bg2};
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }}
        #AdvTitleLabel {{
            color: {text};
            font-weight: 600;
            font-size: 11px;
        }}
        #AdvTitleIcon {{
            color: {accent};
            font-size: 13px;
        }}
        #AdvCloseBtn {{
            background: transparent;
            border: none;
            border-radius: 4px;
        }}
        #AdvCloseBtn:hover {{
            background: {accent};
        }}
        #AdvSep {{ color: {border}; }}
        #AdvTabWrap {{ background: {bg}; }}
        #AdvTabBar::tab {{
            background: {bg2};
            color: {muted};
            padding: 4px 10px;
            border: 1px solid {border};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            font-size: 10px;
        }}
        #AdvTabBar::tab:selected {{
            background: {accent};
            color: {text};
            font-weight: 600;
        }}
        #BTexPreview {{
            border: 1px solid {border};
            border-radius: 4px;
            background: {bg};
        }}
        #BTexBtn {{
            background: {bg2};
            color: {text};
            border: 1px solid {border};
            border-radius: 3px;
            font-size: 10px;
            padding: 0 4px;
        }}
        #BTexBtn:hover {{
            border-color: {accent};
            color: {accent};
        }}
        #CollapsHeader {{
            background: {bg2};
            border-radius: 4px;
        }}
        #CollapsHeader:hover {{
            background: {accent};
        }}
        #CollapsArrow {{ color: {muted}; font-size: 10px; }}
        #CollapsTitle {{
            color: {text};
            font-size: 10px;
            font-weight: 600;
        }}
        #CollapsContent {{
            background: transparent;
        }}
        QStackedWidget, QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
            background: transparent;
            background-color: transparent;
        }}
        QStackedWidget {{
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        }}
        QScrollArea {{
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        }}
        QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
            border-bottom-left-radius: 7px;
            border-bottom-right-radius: 7px;
        }}
        QScrollBar:vertical {{
            border: none;
            background: rgba(0, 0, 0, 0.15);
            width: 7px;
            margin: 2px 2px 8px 2px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical {{
            background: {muted};
            border-radius: 3px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
    """
