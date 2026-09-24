"""DialogActions — abre diálogos e janelas auxiliares e aplica o que eles devolvem.

Filtros, guia, relatório de testes, diagnóstico, atalhos, cursor, idioma,
escala, tema, plugins, renderização e perfil de cor, docas, barra flutuante,
curvas, telemetria (F12), feedback e "sobre". Colaborador da `MainWindow`
(ver `shell_actions.py`); é dono das janelas não modais que reaproveita
(`telemetry_window`, `curve_window`).
"""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.i18n import I18nManager, tr
from ui.core.runtime_paths import resource_path
from ui.core.shortcut_registry import ShortcutRegistry
from ui.core.theme import ThemeManager

from .shell_actions import BackendProvider, ShellActions
from .workspace_port import ShellWorkspace


class DialogActions(ShellActions):
    def __init__(
        self,
        window: QtWidgets.QWidget,
        backend: BackendProvider,
        workspace: Optional[ShellWorkspace],
        shortcuts: ShortcutRegistry,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._backend = backend
        self._workspace = workspace
        self._shortcuts = shortcuts
        self.telemetry_window: Optional[QtWidgets.QWidget] = None
        self.curve_window: Optional[QtWidgets.QWidget] = None

    # ── Filtros e ajuda ───────────────────────────────────────────────────

    def open_filter_dialog(self, filter_key: str | None = None) -> None:
        from ui.core.screens.filters.filter_adjustment_dialog import FilterAdjustmentDialog
        FilterAdjustmentDialog(self._window, initial_key=filter_key).exec()

    def open_diagnostics(self) -> None:
        from ui.core.dialogs.diagnostics_dialog import DiagnosticsDialog
        DiagnosticsDialog(self._window).exec()

    def open_user_guide(self) -> None:
        from ui.core.dialogs.user_guide_dialog import UserGuideDialog
        UserGuideDialog(self._window).exec()

    def open_test_report(self) -> None:
        from ui.core.dialogs.test_report_dialog import TestReportDialog
        TestReportDialog(self._window).exec()

    def open_about(self) -> None:
        from ui.core.screens.about_dialog import AboutDialog
        AboutDialog(self._window).exec()

    def open_feedback_form(self) -> None:
        current_locale = I18nManager.instance().get_current_locale()
        feedback_path = resource_path("Enviar_Feedback.html")
        if feedback_path.is_file():
            url = QtCore.QUrl.fromLocalFile(str(feedback_path))
            url.setQuery(f"lang={current_locale}")
            QtGui.QDesktopServices.openUrl(url)
        else:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(
                f"mailto:lumeniateam@protonmail.com?subject=[Lumenia%20Alpha%20Feedback%20{current_locale}]"
            ))

    # ── Preferências ──────────────────────────────────────────────────────

    def open_shortcuts(self) -> None:
        from ui.core.screens.keyboard_shortcuts_dialog import KeyboardShortcutsDialog
        dialog = KeyboardShortcutsDialog(self._window)
        dialog.shortcutsApplied.connect(self.apply_shortcuts)
        dialog.exec()

    def apply_shortcuts(self, shortcuts_map: dict) -> None:
        self._shortcuts.apply(shortcuts_map)
        self._say(tr("status.shortcuts_applied", "Atalhos de teclado atualizados e aplicados."), 3000)

    def open_cursor_settings(self) -> None:
        from ui.core.screens.cursor_settings_dialog import CursorSettingsDialog
        dialog = CursorSettingsDialog(self._window)
        dialog.cursorSettingsChanged.connect(self.apply_cursor_settings)
        dialog.exec()

    def apply_cursor_settings(self, cfg: dict) -> None:
        if self._workspace is not None:
            self._workspace.canvas_widget.apply_cursor_settings(cfg)
        self._say(tr("status.cursor_applied", "Preferências de cursor aplicadas."), 3000)

    def set_language(self, locale_code: str) -> None:
        mgr = I18nManager.instance()
        if locale_code == "auto":
            mgr.set_auto_mode(emit_signal=True)
            self._say(tr("status.language_changed", "Idioma sincronizado com o sistema operacional."), 3000)
        elif mgr.set_locale(locale_code, is_auto=False, emit_signal=True):
            self._say(tr("status.language_changed", "Idioma alterado com sucesso."), 3000)

    def set_interface_scale(self, scale_value: float) -> None:
        ThemeManager.instance().set_ui_scale(scale_value)
        self._say(tr("status.ui_scale_changed", "Escala da interface alterada para {percent}%.", percent=int(scale_value * 100)), 3000)

    def open_theme_dialog(self) -> None:
        from ui.core.components import ThemeDialog
        ThemeDialog(self._window).exec()

    def open_plugins_dialog(self) -> None:
        from ui.core.screens import PluginsWindow
        PluginsWindow(self._window).exec()

    def open_render_settings(self) -> None:
        from ui.core.dialogs.render_settings_dialog import RenderSettingsDialog
        dialog = RenderSettingsDialog(self._window)
        dialog.profileChanged.connect(self._on_color_profile_changed)
        dialog.exec()

    def _on_color_profile_changed(self, profile_id: int) -> None:
        if self._workspace is not None:
            self._workspace.canvas_widget.update()
            self._workspace.refresh_previews()
        backend = self._backend()
        name = backend.get_color_profile_name(profile_id) if backend else ""
        self._say(tr("status.color_mode_active", "Modo de Cor ativo: {name}", name=name), 3000)

    # ── Workspace (docas e barra flutuante) ───────────────────────────────

    def open_dock_settings(self) -> None:
        if self._workspace is None:
            return
        from ui.core.screens.dock_settings_dialog import DockBarsSettingsDialog
        dialog = DockBarsSettingsDialog(self._workspace.dock_panels(), self._window)
        dialog.settings_applied.connect(self._workspace.apply_dock_settings)
        dialog.exec()

    def open_floating_toolbar_settings(self) -> None:
        if self._workspace is None:
            return
        from ui.core.screens.floating_toolbar_settings_dialog import FloatingToolbarSettingsDialog
        dialog = FloatingToolbarSettingsDialog(self._window)
        dialog.settings_applied.connect(self._workspace.apply_floating_toolbar_settings)
        dialog.exec()

    # ── Janelas não modais (reaproveitadas) ───────────────────────────────

    def open_curve_window(self) -> None:
        if self.curve_window is None:
            from ui.core.screens.curve_window import CurveWindow
            self.curve_window = CurveWindow(self._window)
        self._raise(self.curve_window)

    def open_telemetry_window(self) -> None:
        """Cockpit de telemetria em grade (F12), não modal."""
        if self.telemetry_window is None or not self.telemetry_window.isVisible():
            from ui.core.dialogs.telemetry_grid_window import TelemetryGridWindow
            self.telemetry_window = TelemetryGridWindow(self._window)
        self._raise(self.telemetry_window)
        self._say(tr("status.telemetry_grid_opened", "Cockpit de Telemetria (Grid) ativado."), 3000)

    @staticmethod
    def _raise(window: QtWidgets.QWidget) -> None:
        window.show()
        window.raise_()
        window.activateWindow()
