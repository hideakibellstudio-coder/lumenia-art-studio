"""SettingsMenu — menu Configurações: idioma, renderização, curvas, cursor, atalhos, tema e plugins.

Extraído do `MenuBar` em 2026-09-24 (era montado lá dentro, e o
`retranslate_ui` da barra perguntava `hasattr(self, "act_render")` para cada
ação que ela mesma tinha acabado de criar).
"""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.i18n import I18nManager, tr
from ui.infrastructure.icons import get_icon

class SettingsMenu(QtWidgets.QMenu):
    renderSettingsRequested = QtCore.Signal()
    curvesLutRequested = QtCore.Signal()
    cursorSettingsRequested = QtCore.Signal()
    penCalibrationRequested = QtCore.Signal()
    shortcutsRequested = QtCore.Signal()
    themeSettingsRequested = QtCore.Signal()
    managePluginsRequested = QtCore.Signal()
    languageRequested = QtCore.Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(tr("menu.settings.title", "Configurações"), parent)
        self.language_menu = QtWidgets.QMenu(tr("menu.settings.language", "Idioma (Language)"), self)
        self.language_menu.setIcon(get_icon("settings"))
        self._language_group = QtGui.QActionGroup(self)
        self._language_group.setExclusive(True)
        self._rebuild_language_menu()
        self.addMenu(self.language_menu)

        self._actions: list[tuple[QtGui.QAction, str, str]] = []
        self.act_render = self._action("display", "menu.settings.render", "Renderização & Modos de Cor...",
                                       self.renderSettingsRequested)
        self.act_curves = self._action("curves", "menu.settings.curves", "Curvas LUT (Perfis de Pincel)...",
                                       self.curvesLutRequested)
        self.act_cursor = self._action("cursor", "menu.settings.cursor", "Configurações de Cursor e Ponteiro...",
                                       self.cursorSettingsRequested)
        self.act_pen = self._action("brush", "menu.settings.pen", "Calibrar Caneta (Pressão)...",
                                    self.penCalibrationRequested)
        self.act_shortcuts = self._action("keyboard", "menu.settings.shortcuts", "Atalhos de Teclado...",
                                          self.shortcutsRequested)
        self.act_theme = self._action("palette", "menu.settings.theme", "Personalização de Tema...",
                                      self.themeSettingsRequested)
        self.act_plugins = self._action("plugin", "menu.settings.plugins", "Gerenciador de Plugins...",
                                        self.managePluginsRequested)

    def _action(self, icon: str, key: str, default: str, signal) -> QtGui.QAction:
        action = QtGui.QAction(get_icon(icon), tr(key, default), self)
        action.triggered.connect(signal.emit)
        self._actions.append((action, key, default))
        self.addAction(action)
        return action

    def _rebuild_language_menu(self) -> None:
        self.language_menu.clear()
        mgr = I18nManager.instance()
        is_auto = mgr.is_auto_mode()
        current = mgr.get_current_locale()

        auto = QtGui.QAction(tr("menu.settings.language_auto", "Automático (Sistema)"), self)
        auto.setCheckable(True)
        auto.setChecked(is_auto)
        auto.setData("auto")
        auto.triggered.connect(lambda checked=False: self.languageRequested.emit("auto"))
        self._language_group.addAction(auto)
        self.language_menu.addAction(auto)
        self.language_menu.addSeparator()

        for code, label in mgr.get_available_locales().items():
            action = QtGui.QAction(label, self)
            action.setCheckable(True)
            action.setChecked(not is_auto and code == current)
            action.setData(code)
            action.triggered.connect(lambda checked=False, c=code: self.languageRequested.emit(c))
            self._language_group.addAction(action)
            self.language_menu.addAction(action)

    def retranslate_ui(self) -> None:
        self.setTitle(tr("menu.settings.title", "Configurações"))
        self.language_menu.setTitle(tr("menu.settings.language", "Idioma (Language)"))
        self._rebuild_language_menu()
        for action, key, default in self._actions:
            action.setText(tr(key, default))
