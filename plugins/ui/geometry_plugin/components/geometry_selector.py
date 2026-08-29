"""Geometry Selector Button with 2-Tab Category Grid and Smart Screen Clamping."""

import os
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager
from .constants import GUIDE_TYPES, GUIDE_NAMES, SYM_TYPES, SYM_NAMES

class GeometrySelectorPopup(QtWidgets.QFrame):
    """Popup flutuante de seleção com 2 abas (Réguas / Simetrias) e grid de opções."""

    rulerSelected = QtCore.Signal(int)
    symmetrySelected = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_ruler_idx = 0
        self.active_sym_idx = 0
        self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
        self.setWindowFlags(QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint | QtCore.Qt.NoDropShadowWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setFixedSize(330, 250)
        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self, *args):
        tm = ThemeManager.instance()
        bg_card = tm.get_color("bg_card", "#181825")
        bg_panel = tm.get_color("bg_panel", "#1e1e24")
        border = tm.get_color("border", "#313244")
        accent = tm.get_color("accent", "#6366f1")
        text_main = tm.get_color("text_main", "#f3f4f6")
        text_sec = tm.get_color("text_sec", "#9ca3af")
        bg_hover = tm.get_color("accent_muted", "#4f46e5")

        self.container.setStyleSheet(f"""
            QFrame {{ background-color: {bg_card}; border: 1px solid {border}; border-radius: 8px; }}
            QPushButton.tab-btn {{
                background: transparent; color: {text_sec}; border: none;
                border-bottom: 2px solid transparent; padding: 6px; font-weight: bold; font-size: 11px;
            }}
            QPushButton.tab-btn:checked {{
                color: {text_main}; border-bottom: 2px solid {accent};
            }}
            QPushButton.grid-item {{
                background: {bg_panel}; color: {text_main}; border: 1px solid {border};
                border-radius: 4px; padding: 5px 8px; font-size: 11px; text-align: left;
            }}
            QPushButton.grid-item:hover {{
                background: {bg_hover}; border-color: {accent};
            }}
            QPushButton.grid-item:checked {{
                background: {accent}; border-color: {accent}; font-weight: bold; color: #ffffff;
            }}
        """)

    def _build_ui(self):
        main_lay = QtWidgets.QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)

        self.container = QtWidgets.QFrame()
        c_lay = QtWidgets.QVBoxLayout(self.container)
        c_lay.setContentsMargins(8, 8, 8, 8)
        c_lay.setSpacing(6)

        # Tab Bar
        tabs = QtWidgets.QHBoxLayout()
        self.btn_tab_ruler = QtWidgets.QPushButton("📏  Réguas & Guias")
        self.btn_tab_ruler.setProperty("class", "tab-btn")
        self.btn_tab_ruler.setCheckable(True)
        self.btn_tab_ruler.setChecked(True)

        self.btn_tab_sym = QtWidgets.QPushButton("🪞  Simetrias")
        self.btn_tab_sym.setProperty("class", "tab-btn")
        self.btn_tab_sym.setCheckable(True)

        self.btn_tab_ruler.clicked.connect(lambda: self._switch_tab(0))
        self.btn_tab_sym.clicked.connect(lambda: self._switch_tab(1))
        tabs.addWidget(self.btn_tab_ruler, 1)
        tabs.addWidget(self.btn_tab_sym, 1)
        c_lay.addLayout(tabs)

        # Stacked Pages
        self.stack = QtWidgets.QStackedWidget()

        # Page 0: Réguas
        page_ruler = QtWidgets.QWidget()
        grid_r = QtWidgets.QGridLayout(page_ruler)
        grid_r.setSpacing(6)
        grid_r.setContentsMargins(0, 4, 0, 0)
        self.ruler_buttons = []
        for idx, (gtype, gname) in enumerate(zip(GUIDE_TYPES, GUIDE_NAMES)):
            btn = QtWidgets.QPushButton(gname)
            btn.setProperty("class", "grid-item")
            btn.setCheckable(True)
            icon_file = os.path.join(self.assets_dir, f"ruler_{gtype}.svg") if gtype != "none" else ""
            if icon_file and os.path.exists(icon_file):
                btn.setIcon(QtGui.QIcon(icon_file))
                btn.setIconSize(QtCore.QSize(16, 16))
            btn.clicked.connect(lambda _, i=idx: self._select_ruler(i))
            grid_r.addWidget(btn, idx // 2, idx % 2)
            self.ruler_buttons.append(btn)
        self.stack.addWidget(page_ruler)

        # Page 1: Simetrias
        page_sym = QtWidgets.QWidget()
        grid_s = QtWidgets.QGridLayout(page_sym)
        grid_s.setSpacing(6)
        grid_s.setContentsMargins(0, 4, 0, 0)
        self.sym_buttons = []
        for idx, (stype, sname) in enumerate(zip(SYM_TYPES, SYM_NAMES)):
            btn = QtWidgets.QPushButton(sname)
            btn.setProperty("class", "grid-item")
            btn.setCheckable(True)
            icon_file = os.path.join(self.assets_dir, f"symmetry_{stype}.svg") if stype != "none" else ""
            if icon_file and os.path.exists(icon_file):
                btn.setIcon(QtGui.QIcon(icon_file))
                btn.setIconSize(QtCore.QSize(16, 16))
            btn.clicked.connect(lambda _, i=idx: self._select_sym(i))
            grid_s.addWidget(btn, idx // 2, idx % 2)
            self.sym_buttons.append(btn)
        self.stack.addWidget(page_sym)

        c_lay.addWidget(self.stack, 1)
        main_lay.addWidget(container)

    def _switch_tab(self, idx: int):
        self.stack.setCurrentIndex(idx)
        self.btn_tab_ruler.setChecked(idx == 0)
        self.btn_tab_sym.setChecked(idx == 1)

    def set_active_selections(self, ruler_idx: int, sym_idx: int):
        self.active_ruler_idx = ruler_idx
        self.active_sym_idx = sym_idx
        for i, b in enumerate(self.ruler_buttons):
            b.setChecked(i == ruler_idx)
        for i, b in enumerate(self.sym_buttons):
            b.setChecked(i == sym_idx)

    def _select_ruler(self, idx: int):
        self.rulerSelected.emit(idx)
        self.close()

    def _select_sym(self, idx: int):
        self.symmetrySelected.emit(idx)
        self.close()


class GeometrySelectorButton(QtWidgets.QPushButton):
    """Botão da barra superior do painel que abre o popup perfeitamente encaixado."""

    ruler_changed = QtCore.Signal(int, str)
    symmetry_changed = QtCore.Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_ruler_idx = 0
        self.active_sym_idx = 0
        self.popup = None

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(34)
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()
        self._update_text()
        self.clicked.connect(self._open_popup)

    def _apply_theme(self, *args):
        tm = ThemeManager.instance()
        bg_panel = tm.get_color("bg_panel", "#1e1e24")
        border = tm.get_color("border", "#3b3b54")
        accent = tm.get_color("accent", "#6366f1")
        text_main = tm.get_color("text_main", "#e2e8f0")
        bg_hover = tm.get_color("accent_muted", "#28283d")

        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg_panel}; color: {text_main}; border: 1px solid {border};
                border-radius: 6px; padding: 4px 10px; font-weight: bold; text-align: left;
            }}
            QPushButton:hover {{ background: {bg_hover}; border-color: {accent}; }}
        """)

    def _update_text(self):
        r_name = GUIDE_NAMES[self.active_ruler_idx] if self.active_ruler_idx < len(GUIDE_NAMES) else "None"
        s_name = SYM_NAMES[self.active_sym_idx] if self.active_sym_idx < len(SYM_NAMES) else "None"
        if self.active_ruler_idx == 0 and self.active_sym_idx == 0:
            self.setText("📐  Geometria: Desativada  ▾")
        elif self.active_ruler_idx > 0 and self.active_sym_idx == 0:
            self.setText(f"📏  Régua: {r_name}  ▾")
        elif self.active_ruler_idx == 0 and self.active_sym_idx > 0:
            self.setText(f"🪞  Simetria: {s_name}  ▾")
        else:
            self.setText(f"📐  {r_name} | {s_name}  ▾")

    def _open_popup(self):
        if not self.popup:
            self.popup = GeometrySelectorPopup(self.window())
            self.popup.rulerSelected.connect(self._on_ruler_sel)
            self.popup.symmetrySelected.connect(self._on_sym_sel)

        self.popup.set_active_selections(self.active_ruler_idx, self.active_sym_idx)
        pos = self.mapToGlobal(QtCore.QPoint(0, self.height() + 4))
        screen = self.screen().availableGeometry() if self.screen() else QtCore.QRect(0, 0, 1920, 1080)
        popup_w, popup_h = self.popup.width(), self.popup.height()

        x = pos.x() + self.width() - popup_w
        if x < screen.left() + 10:
            x = screen.left() + 10
        if x + popup_w > screen.right() - 10:
            x = screen.right() - popup_w - 10
        y = pos.y()
        if y + popup_h > screen.bottom() - 10:
            y = self.mapToGlobal(QtCore.QPoint(0, 0)).y() - popup_h - 4

        self.popup.setGeometry(x, y, popup_w, popup_h)
        self.popup.show()
        self.popup.raise_()

    def _on_ruler_sel(self, idx: int):
        self.active_ruler_idx = idx
        self._update_text()
        gtype = GUIDE_TYPES[idx] if idx < len(GUIDE_TYPES) else "none"
        self.ruler_changed.emit(idx, gtype)

    def _on_sym_sel(self, idx: int):
        self.active_sym_idx = idx
        self._update_text()
        stype = SYM_TYPES[idx] if idx < len(SYM_TYPES) else "none"
        self.symmetry_changed.emit(idx, stype)
