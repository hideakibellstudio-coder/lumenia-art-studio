"""Seleção de ferramenta, câmera (zoom/reset) e tela cheia da MainWindow.

Separado de main_window.py em 2026-09-22 (442 linhas, na parede dos 450).
"""
from ui.core.components import ToolSidebar


class MainWindowToolCameraActionsMixin:
    """Mixin extraído de main_window.py (métodos movidos sem alteração)."""

    # ── Ferramenta ────────────────────────────────────────────────────────

    def _on_dock_tool_activated(self, tool_id: str) -> None:
        """Sincroniza ToolSidebar quando a ferramenta muda via BrushDock."""
        if tool_id == "brush":
            self.tool_sidebar.action_brush.setChecked(True)
            self.tool_sidebar.action_eraser.setChecked(False)
        elif tool_id == "eraser":
            self.tool_sidebar.action_brush.setChecked(False)
            self.tool_sidebar.action_eraser.setChecked(True)

    def select_brush_tool(self) -> None:
        self.select_tool_by_id("brush")

    def select_eraser_tool(self) -> None:
        self.select_tool_by_id("eraser")

    def select_shapes_tool(self) -> None:
        self.select_tool_by_id("shapes")

    def select_text_tool(self) -> None:
        self.select_tool_by_id("text")

    def select_tool_by_id(self, tool_id: str) -> None:
        if self.workspace:
            self.workspace.select_tool(tool_id)
        if hasattr(self, "tool_sidebar"):
            self.tool_sidebar.action_brush.setChecked(tool_id == "brush")
            self.tool_sidebar.action_eraser.setChecked(tool_id == "eraser")
            if hasattr(self.tool_sidebar, "action_shapes"):
                self.tool_sidebar.action_shapes.setChecked(tool_id.startswith("shape") or tool_id == "shapes")
        
        from ui.core.tools import TOOL_META
        tool_name = TOOL_META.get(tool_id, {}).get("name", tool_id.capitalize())
        self.status_bar.showMessage(f"Ferramenta {tool_name} selecionada.")

    # ── Câmera ────────────────────────────────────────────────────────────

    def reset_view(self) -> None:
        if self.workspace:
            self.workspace.reset_view()
        self.status_bar.showMessage("Visão do canvas resetada.", 2000)

    def zoom_in(self) -> None:
        if self.workspace:
            self.workspace.zoom_in()

    def zoom_out(self) -> None:
        if self.workspace:
            self.workspace.zoom_out()

    def toggle_fullscreen(self) -> None:
        """Alterna entre modo tela cheia e modo normal/maximizado."""
        from ui.core.i18n import tr
        if self.isFullScreen():
            self.showMaximized() if getattr(self, "_was_maximized_before_fullscreen", False) else self.showNormal()
            msg = tr("status.fullscreen_off", "Modo normal restaurado.")
        else:
            self._was_maximized_before_fullscreen = self.isMaximized()
            self.showFullScreen()
            msg = tr("status.fullscreen_on", "Modo Tela Cheia ativado. Pressione F11 para sair.")

        if getattr(self, "status_bar", None):
            self.status_bar.showMessage(msg, 3500)
        vm = getattr(getattr(self, "menu_bar", None), "view_menu", None)
        if vm and hasattr(vm, "action_fullscreen"):
            vm.action_fullscreen.setChecked(self.isFullScreen())
