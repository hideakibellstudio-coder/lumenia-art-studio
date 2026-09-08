"""
MainWindowDialogActionsMixin — Despacho e Abertura de Diálogos e Janelas
=========================================================================
Mixin especializado no acionamento de diálogos modais e não-modais da aplicação:
- Filtros e ajustes de imagem
- Guia do usuário, relatório de testes e sobre
- Preferências de cursor, atalhos de teclado e idioma
- Cockpit de telemetria em tempo real (F12) e formulário de feedback
"""

from __future__ import annotations

import os
from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.dialogs.diagnostics_dialog import DiagnosticsDialog
from ui.core.screens.filters.filter_adjustment_dialog import FilterAdjustmentDialog


class MainWindowDialogActionsMixin:
    """Mixin contendo as ações de acionamento de diálogos, telas auxiliares e configurações."""

    def open_filter_gallery(self) -> None:
        self.open_filter_dialog()

    def open_filter_dialog(self, filter_key: str | None = None) -> None:
        dialog = FilterAdjustmentDialog(self, initial_key=filter_key)
        dialog.exec()

    def open_diagnostics_dialog(self) -> None:
        dialog = DiagnosticsDialog(self)
        dialog.exec()

    def open_user_guide(self) -> None:
        from ui.core.dialogs.user_guide_dialog import UserGuideDialog
        dialog = UserGuideDialog(self)
        dialog.exec()

    def open_test_report_dialog(self) -> None:
        from ui.core.dialogs.test_report_dialog import TestReportDialog
        dialog = TestReportDialog(self)
        dialog.exec()

    def open_shortcuts_dialog(self) -> None:
        from ui.core.screens.keyboard_shortcuts_dialog import KeyboardShortcutsDialog
        dialog = KeyboardShortcutsDialog(self)
        dialog.shortcutsApplied.connect(self._on_shortcuts_applied)
        dialog.exec()

    def _on_shortcuts_applied(self, shortcuts_map: dict) -> None:
        if not shortcuts_map:
            return

        shortcut_targets = {
            "tool_brush": "shortcut_tool_b",
            "tool_eraser": "shortcut_tool_e",
            "tool_shapes": "shortcut_tool_u",
            "tool_text": "shortcut_tool_t",
            "edit_undo": "shortcut_undo",
            "edit_redo": "shortcut_redo_y",
        }

        for item_id, attr_name in shortcut_targets.items():
            if item_id in shortcuts_map and hasattr(self, attr_name):
                shortcut_obj = getattr(self, attr_name)
                seq = shortcuts_map[item_id]
                if not seq:
                    continue
                if isinstance(shortcut_obj, QtGui.QShortcut):
                    shortcut_obj.setKey(QtGui.QKeySequence(seq))
                elif isinstance(shortcut_obj, QtGui.QAction):
                    shortcut_obj.setShortcut(QtGui.QKeySequence(seq))

        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.showMessage("Atalhos de teclado atualizados e aplicados.", 3000)

    def open_cursor_settings_dialog(self) -> None:
        from ui.core.screens.cursor_settings_dialog import CursorSettingsDialog
        dialog = CursorSettingsDialog(self)
        dialog.cursorSettingsChanged.connect(self._on_cursor_settings_changed)
        dialog.exec()

    def _on_cursor_settings_changed(self, cfg: dict) -> None:
        cw = getattr(self.workspace, "canvas_widget", None)
        if cw:
            cw._cursor_settings = cfg
            if hasattr(cw, "_update_cursor_shape"):
                cw._update_cursor_shape()
            cw.update()
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.showMessage("Preferências de cursor aplicadas.", 3000)

    def open_feedback_form(self) -> None:
        from ui.core.i18n import I18nManager
        current_locale = I18nManager.instance().get_current_locale()
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        feedback_path = os.path.join(project_root, "Enviar_Feedback.html")
        if os.path.exists(feedback_path):
            url = QtCore.QUrl.fromLocalFile(feedback_path)
            url.setQuery(f"lang={current_locale}")
            QtGui.QDesktopServices.openUrl(url)
        else:
            QtGui.QDesktopServices.openUrl(
                QtCore.QUrl(f"mailto:lumeniateam@protonmail.com?subject=[Lumenia%20Alpha%20Feedback%20{current_locale}]")
            )

    def open_about_dialog(self) -> None:
        from ui.core.screens.about_dialog import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()

    def load_custom_texture(self, is_shape: bool) -> None:
        self.workspace._load_custom_texture(is_shape)
        kind = "Shape" if is_shape else "Heightmap"
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.showMessage(f"Textura {kind} carregada.", 3000)

    def set_application_language(self, locale_code: str) -> None:
        from ui.core.i18n import I18nManager, tr
        mgr = I18nManager.instance()
        if locale_code == "auto":
            mgr.set_auto_mode(emit_signal=True)
            msg = tr("status.language_changed", "Idioma sincronizado com o sistema operacional.")
            if hasattr(self, "status_bar") and self.status_bar:
                self.status_bar.showMessage(msg, 3000)
        elif mgr.set_locale(locale_code, is_auto=False, emit_signal=True):
            msg = tr("status.language_changed", "Idioma alterado com sucesso.")
            if hasattr(self, "status_bar") and self.status_bar:
                self.status_bar.showMessage(msg, 3000)

    def open_telemetry_grid_window(self) -> None:
        """Abre a janela flutuante não-modal do Cockpit de Telemetria em Grid (F12)."""
        from ui.core.dialogs.telemetry_grid_window import TelemetryGridWindow
        if not hasattr(self, "_telemetry_grid_win") or self._telemetry_grid_win is None or not self._telemetry_grid_win.isVisible():
            self._telemetry_grid_win = TelemetryGridWindow(self)
        self._telemetry_grid_win.show()
        self._telemetry_grid_win.raise_()
        self._telemetry_grid_win.activateWindow()
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.showMessage("Cockpit de Telemetria (Grid) ativado.", 3000)
