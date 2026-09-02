"""AdvancedDockSystem — Sistema de Gavetas Dinâmicas com Auto-Recolhimento (ARCcC)."""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Set
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.logger import get_logger
from .dock.sidebar_button import SidebarButton
from .dock.sidebar_widget import SidebarWidget
from .dock.drawer_header import DrawerHeader
from .dock.drawer_content_container import DrawerContentContainer

if TYPE_CHECKING:
    from plugins.system.workspace_core.workspace.workspace_container import WorkspaceContainer

logger = get_logger("Workspace.DockSystem")

SPEED_MAP = {"Ultra Rápido": 60, "Rápido": 180, "Normal": 320, "Lento": 500}
DELAY_MAP = {"Sem Atraso": 0, "Curto (100ms)": 100, "Normal (350ms)": 350, "Longo (800ms)": 800}


class AdvancedDockSystem(QtWidgets.QWidget):
    """Gerenciador da Doca Lateral (Esquerda ou Direita) com auto-recolhimento e gavetas."""

    drawer_opened = QtCore.Signal(str)   # panel_id ou "stacked"
    drawer_closed = QtCore.Signal()
    pin_toggled = QtCore.Signal(bool)
    layout_order_changed = QtCore.Signal(list)  # [panel_id, ...]

    # Largura total (sidebar expandida)
    SIDEBAR_EXPANDED = 54

    def __init__(
        self,
        side: str,                        # "left" | "right"
        parent_workspace: WorkspaceContainer,
    ) -> None:
        super().__init__(parent_workspace)
        self.side = side
        self._workspace = parent_workspace

        self._outer_layout = QtWidgets.QHBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._outer_layout.setSpacing(0)

        # ── Estado Interno ─────────────────────────────────────────────
        self.is_pinned:      bool = False
        self.is_open:        bool = False
        self.active_panel_ids: Set[str] = set()
        self._is_painting:   bool = False

        # ── Configurações de animação ──────────────────────────────────
        self._auto_collapse:  bool = False
        self._speed_ms:       int  = SPEED_MAP["Rápido"]
        self._hover_delay_ms: int  = DELAY_MAP["Normal (350ms)"]

        # ── Componentes ───────────────────────────────────────────────
        self.sidebar          = SidebarWidget(side, self)
        self.drawer_container = DrawerContentContainer(side=side, parent=self)

        self._panels_info: Dict[str, dict] = {}

        # ── Animação da Sidebar ────────────────────────────────────────
        self._sidebar_anim = QtCore.QPropertyAnimation(self.sidebar, b"maximumWidth")
        self._sidebar_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._sidebar_anim.valueChanged.connect(self._on_sidebar_anim_value_changed)
        self._sidebar_anim.finished.connect(self._on_sidebar_anim_finished)

        # ── Animação da Gaveta (DrawerContentContainer) ────────────────
        self._drawer_anim = QtCore.QPropertyAnimation(self.drawer_container, b"maximumWidth")
        self._drawer_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self._drawer_anim.valueChanged.connect(self._on_drawer_anim_value_changed)
        self._drawer_anim.finished.connect(self._on_drawer_anim_finished)

        self._update_anim_duration()

        # ── Timers de Auto-Recolhimento ────────────────────────────────
        self._collapse_timer = QtCore.QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._do_collapse)

        self._expand_timer = QtCore.QTimer(self)
        self._expand_timer.setSingleShot(True)
        self._expand_timer.timeout.connect(self._do_expand)

        # ── Hover da Sidebar (auto-recolhimento) ──────────────────────
        self.sidebar.installEventFilter(self)

        # ── Conexões ──────────────────────────────────────────────────
        self.sidebar.button_clicked.connect(self.toggle_panel)
        self.drawer_container.header.pin_toggled.connect(self.set_pinned)
        self.drawer_container.header.pin_toggled.connect(self.pin_toggled.emit)

        # ── Inserção no layout ─────────────────────────────────────────
        self._outer_layout.addWidget(self.sidebar)
        self.drawer_container.hide()

        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

        # ── PillHandle (injetado posteriormente pelo WorkspaceContainer) ──
        self._pill: object = None  # Referência à PillHandle

    @property
    def effective_left_x(self) -> int:
        """Retorna a coordenada X global da borda esquerda da doca (incluindo gaveta se aberta)."""
        base_x = self.mapToGlobal(QtCore.QPoint(0, 0)).x()
        if hasattr(self, "drawer_container") and self.drawer_container.isVisible():
            drawer_x = self.drawer_container.mapToGlobal(QtCore.QPoint(0, 0)).x()
            return min(base_x, drawer_x)
        return base_x

    @property
    def effective_right_x(self) -> int:
        """Retorna a coordenada X global da borda direita da doca (incluindo gaveta se aberta)."""
        base_x = self.mapToGlobal(QtCore.QPoint(self.width(), 0)).x()
        if hasattr(self, "drawer_container") and self.drawer_container.isVisible():
            dw = self.drawer_container.width()
            drawer_x = self.drawer_container.mapToGlobal(QtCore.QPoint(dw, 0)).x()
            return max(base_x, drawer_x)
        return base_x

    @property
    def visual_width(self) -> int:
        """Retorna a largura visual total ocupada pela doca (sidebar + gaveta se visível)."""
        if self.is_pinned:
            return self.width()
        w = self.sidebar.width() if self.sidebar.isVisible() else 0
        if self.is_open and hasattr(self, "drawer_container") and self.drawer_container.isVisible():
            w += self.drawer_container.width()
        return w

    # ── Configurações ─────────────────────────────────────────────────────

    def apply_settings(
        self,
        auto_collapse: bool,
        speed: str = "Rápido",
        delay: str = "Normal (350ms)",
    ) -> None:
        """Atualiza configurações de comportamento em tempo real."""
        self._auto_collapse  = auto_collapse
        self._speed_ms       = SPEED_MAP.get(speed, 180)
        self._hover_delay_ms = DELAY_MAP.get(delay, 350)
        self._update_anim_duration()

        if self._auto_collapse or self.is_pinned:
            # Se auto_collapse ou pin estiver ativo e o mouse não está sobre a sidebar, recolhe
            if not self.sidebar.underMouse() and (not self.is_open or self.is_pinned):
                self._do_collapse()
        else:
            # Auto-recolhimento desligado e não pinada → expande a sidebar e para timers
            self._collapse_timer.stop()
            self._expand_timer.stop()
            if self.sidebar.maximumWidth() == 0:
                self._do_expand()

    def _update_anim_duration(self) -> None:
        self._sidebar_anim.setDuration(self._speed_ms)
        self._drawer_anim.setDuration(int(self._speed_ms * 1.2) + 40)

    # ── PillHandle ────────────────────────────────────────────────────────

    def inject_pill(self, pill: object) -> None:
        """Recebe a PillHandle criada pelo WorkspaceContainer e conecta os sinais."""
        self._pill = pill
        pill.hovered.connect(self._on_pill_hovered)
        pill.left.connect(self._on_pill_left)

    def _on_pill_hovered(self) -> None:
        if not self._is_painting:
            self._expand_timer.start(self._hover_delay_ms)

    def _on_pill_left(self) -> None:
        self._expand_timer.stop()

    def _show_pill(self) -> None:
        if self._pill:
            try:
                self._pill.show()
                self._pill.raise_()
            except RuntimeError:
                pass

    def _hide_pill(self) -> None:
        if self._pill:
            try:
                self._pill.hide()
            except RuntimeError:
                pass

    # ── Animação Sidebar ──────────────────────────────────────────────────

    def _do_collapse(self) -> None:
        """Anima a sidebar de 54px → 0px."""
        self._expand_timer.stop()
        current = self.sidebar.width()
        if current == 0 or not self.sidebar.isVisible():
            self.sidebar.hide()
            self._show_pill()
            return
        self._sidebar_anim.stop()
        self._sidebar_anim.setStartValue(current)
        self._sidebar_anim.setEndValue(0)
        self._sidebar_anim.start()

    def _do_expand(self) -> None:
        """Anima a sidebar de 0px → 54px (somente se não estiver pintando)."""
        if self._is_painting:
            return
        self._collapse_timer.stop()
        self._hide_pill()
        self.sidebar.show()
        self.sidebar.raise_()
        current = self.sidebar.width()
        if current == self.SIDEBAR_EXPANDED and not self.sidebar.isHidden():
            self.sidebar.setFixedWidth(self.SIDEBAR_EXPANDED)
            return
        self._sidebar_anim.stop()
        self._sidebar_anim.setStartValue(current)
        self._sidebar_anim.setEndValue(self.SIDEBAR_EXPANDED)
        self._sidebar_anim.start()

    def _on_sidebar_anim_value_changed(self, value: int) -> None:
        self.sidebar.setFixedWidth(value)
        if hasattr(self._workspace, "_update_pill_positions"):
            self._workspace._update_pill_positions()

    def _on_sidebar_anim_finished(self) -> None:
        """Quando a sidebar terminar de recolher, exibe a pílula."""
        if self.sidebar.width() == 0:
            self.sidebar.hide()
            self._show_pill()
        else:
            self.sidebar.setFixedWidth(self.SIDEBAR_EXPANDED)
            self._hide_pill()
        # Atualiza a posição da pílula via workspace
        if hasattr(self._workspace, "_update_pill_positions"):
            self._workspace._update_pill_positions()

    # ── Event Filter — Hover da Sidebar ──────────────────────────────────

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched is self.sidebar:
            if event.type() == QtCore.QEvent.Leave:
                self._on_sidebar_leave()
            elif event.type() == QtCore.QEvent.Enter:
                self._on_sidebar_enter()
        return super().eventFilter(watched, event)

    def _on_sidebar_enter(self) -> None:
        self._collapse_timer.stop()

    def _on_sidebar_leave(self) -> None:
        # Não recolhe se a gaveta despinada está aberta (o usuário está interagindo)
        if self.is_open and not self.is_pinned:
            return
        # Recolhe se auto_collapse ou is_pinned estiver ativo
        if self._auto_collapse or self.is_pinned:
            if not self.sidebar.underMouse():
                self._collapse_timer.start(self._speed_ms)

    # ── Gestão de Painéis ─────────────────────────────────────────────────

    def add_panel(
        self,
        panel_id: str,
        title: str,
        widget: QtWidgets.QWidget,
        icon_path: str | None = None,
    ) -> None:
        self._panels_info[panel_id] = {"title": title, "widget": widget}
        self.sidebar.add_panel_button(panel_id, title, icon_path)
        self.drawer_container.add_panel_widget(panel_id, title, widget)

    def remove_panel(self, panel_id: str) -> None:
        if panel_id in self._panels_info:
            del self._panels_info[panel_id]
            self.active_panel_ids.discard(panel_id)
            self.sidebar.remove_panel_button(panel_id)
            self.drawer_container.remove_panel_widget(panel_id)
            if not self.active_panel_ids:
                self.close_drawer()

    def _cleanup_panels(self) -> None:
        """Remove referências a objetos C++ já destruídos (descarregamento dinâmico de plugins)."""
        dead_panels  = []
        dead_buttons = []

        for pid, widget in list(self.drawer_container._panels.items()):
            try:
                widget.parent()
            except RuntimeError:
                dead_panels.append(pid)

        for pid in dead_panels:
            self.drawer_container._panels.pop(pid, None)
            self._panels_info.pop(pid, None)
            self.active_panel_ids.discard(pid)

        for pid, btn in list(self.sidebar._buttons.items()):
            try:
                btn.parent()
            except RuntimeError:
                dead_buttons.append(pid)

        for pid in dead_buttons:
            self.sidebar._buttons.pop(pid, None)

    # ── Lógica de Empilhamento Acumulativo ────────────────────────────────

    def toggle_panel(self, panel_id: str) -> None:
        """Alterna a visibilidade individual do painel dentro da gaveta empilhada."""
        self._cleanup_panels()
        if panel_id not in self._panels_info:
            return

        widget = self.drawer_container._panels.get(panel_id)
        if not widget:
            return

        try:
            if panel_id in self.active_panel_ids:
                self.active_panel_ids.remove(panel_id)
                self.sidebar.set_button_active(panel_id, False)
                widget.hide()
                logger.info(f"Gaveta '{self.side}': desativou '{panel_id}'. Restantes: {list(self.active_panel_ids)}")
            else:
                self.active_panel_ids.add(panel_id)
                self.sidebar.set_button_active(panel_id, True)
                widget.show()
                logger.info(f"Gaveta '{self.side}': ativou '{panel_id}'. Ativos: {list(self.active_panel_ids)}")
        except RuntimeError:
            self.active_panel_ids.discard(panel_id)
            return

        self.drawer_container.update_spacer(self.active_panel_ids)
        self._update_drawer_state()

    def retranslate_ui(self):
        from ui.core.i18n import tr
        panel_i18n = {
            "brush": ("menu.window.brush_panel", "Pincel & Ferramentas"),
            "color_wheel": ("menu.window.color_wheel", "Cores & Harmonias"),
            "navigator": ("menu.window.navigator", "Navegador do Canvas"),
            "layers": ("menu.window.layers_panel", "Camadas"),
            "geometry": ("menu.window.geometry_guides", "Guias de Perspectiva"),
            "symmetry": ("menu.window.symmetry_panel", "Estúdio de Simetria"),
            "palette": ("menu.window.palette_panel", "Paletas de Cores"),
            "telemetry": ("help.diagnostics", "Diagnósticos & Telemetria"),
        }
        for panel_id, btn in self.sidebar._buttons.items():
            if panel_id in panel_i18n:
                key, def_val = panel_i18n[panel_id]
                trans = tr(key, def_val)
                btn.setToolTip(trans)
                if panel_id in self._panels_info:
                    self._panels_info[panel_id]["title"] = trans

        if self.is_open:
            self._update_drawer_state()

    def _update_drawer_state(self) -> None:
        """Atualiza título do cabeçalho e abre/fecha a gaveta conforme painéis ativos."""
        count = len(self.active_panel_ids)

        if count == 0:
            self.close_drawer()
        elif count == 1:
            active_pid = next(iter(self.active_panel_ids))
            title = self._panels_info.get(active_pid, {}).get("title", "")
            self.drawer_container.header.set_title(title)
            if not self.is_open:
                self.is_open = True
                self.resolve_state()
                self.drawer_opened.emit(active_pid)
        else:
            from ui.core.i18n import tr
            self.drawer_container.header.set_title(tr("window.stacked_panels", "PAINÉIS EMPILHADOS"))
            if not self.is_open:
                self.is_open = True
                self.resolve_state()
                self.drawer_opened.emit("stacked")

    def close_drawer(self) -> None:
        """Fecha a gaveta e desmarca todos os painéis ativos."""
        self._cleanup_panels()
        self.is_open = False
        for pid in list(self.active_panel_ids):
            self.sidebar.set_button_active(pid, False)
            widget = self.drawer_container._panels.get(pid)
            if widget:
                try:
                    widget.hide()
                except RuntimeError:
                    pass
        self.active_panel_ids.clear()
        self.drawer_container.update_spacer(self.active_panel_ids)
        self.resolve_state()
        self.drawer_closed.emit()

        # Quando fecha a gaveta, avalia se deve recolher a sidebar:
        # recolhe tanto no modo auto_collapse quanto quando a gaveta estava pinada
        if (self._auto_collapse or self.is_pinned) and not self.sidebar.underMouse():
            self._collapse_timer.start(self._speed_ms)

    def set_pinned(self, pinned: bool) -> None:
        self.is_pinned = pinned
        self.drawer_container.header.set_pinned(pinned)
        if self.is_open:
            self.resolve_state()
        # Ao pinar: sidebar recolhe automaticamente para dar espaço ao painel inline
        if pinned and not self.sidebar.underMouse():
            self._do_collapse()
        # Ao despinar: expande a sidebar de volta
        elif not pinned:
            self._do_expand()

    # ── Animação da Gaveta ────────────────────────────────────────────────

    DRAWER_WIDTH = 280

    def open_drawer_anim(self) -> None:
        """Inicia animação de expansão suave da gaveta (0 → 280px)."""
        self.drawer_container.show()
        if not self.is_pinned:
            self.drawer_container.raise_()
        current = self.drawer_container.maximumWidth()
        if current == self.DRAWER_WIDTH and self.drawer_container.width() == self.DRAWER_WIDTH:
            self.drawer_container.setMinimumWidth(self.DRAWER_WIDTH)
            if not self.is_pinned:
                self.update_unpinned_position()
            return
        self._drawer_anim.stop()
        self._drawer_anim.setStartValue(current)
        self._drawer_anim.setEndValue(self.DRAWER_WIDTH)
        self._drawer_anim.start()

    def close_drawer_anim(self) -> None:
        """Inicia animação de colapso suave da gaveta (280 → 0px)."""
        current = self.drawer_container.maximumWidth()
        if current == 0:
            self.drawer_container.hide()
            return
        self.drawer_container.setMinimumWidth(0)
        self._drawer_anim.stop()
        self._drawer_anim.setStartValue(current)
        self._drawer_anim.setEndValue(0)
        self._drawer_anim.start()

    def _on_drawer_anim_value_changed(self, value: int) -> None:
        self.drawer_container.setMinimumWidth(value)
        if not self.is_pinned and self.drawer_container.isVisible():
            self.update_unpinned_position()

    def _on_drawer_anim_finished(self) -> None:
        if self.drawer_container.maximumWidth() == 0:
            self.drawer_container.hide()
            for widget in self.drawer_container._panels.values():
                try:
                    widget.hide()
                except RuntimeError:
                    pass
        else:
            self.drawer_container.setMinimumWidth(self.DRAWER_WIDTH)
            self.drawer_container.setMaximumWidth(self.DRAWER_WIDTH)
            if not self.is_pinned:
                self.update_unpinned_position()

    def resolve_state(self) -> None:
        """
        Resolve o estado das gavetas com reparentamento seguro e animação suave.

        - Pinned: gaveta inserida no layout da doca (empurra o canvas).
        - Unpinned: gaveta reparentada para workspace_area, flutuante.
        """
        if not self.is_open:
            self.close_drawer_anim()
            return

        target_parent = getattr(self._workspace, "workspace_area", self._workspace)

        if self.is_pinned:
            if self._outer_layout.indexOf(self.drawer_container) == -1:
                self.drawer_container.setParent(self)
                if self.side == "left":
                    self._outer_layout.insertWidget(1, self.drawer_container)
                else:
                    self._outer_layout.insertWidget(0, self.drawer_container)
        else:
            if self._outer_layout.indexOf(self.drawer_container) != -1:
                self._outer_layout.removeWidget(self.drawer_container)
            self.drawer_container.setParent(target_parent)
            self.update_unpinned_position()

        self.open_drawer_anim()
        if not self.is_pinned:
            self.update_unpinned_position()

    def update_unpinned_position(self) -> None:
        """Posiciona a gaveta flutuante no workspace_area colada ao slot de 54px da sidebar."""
        if self.is_pinned:
            return
        if not self.is_open and self.drawer_container.maximumWidth() == 0:
            return

        target_parent = getattr(self._workspace, "workspace_area", self._workspace)
        sb_h     = target_parent.height()
        drawer_w = max(1, self.drawer_container.maximumWidth())

        if self.side == "left":
            # Doca esquerda flutuante: posiciona imediatamente após a faixa de 54px da sidebar esquerda
            pos_x = 54
        else:
            # Doca direita flutuante: a sidebar ocupa a faixa W-54..W.
            # A gaveta fica posiciomada imediatamente à esquerda (W - 54 - drawer_w..W - 54),
            # garantindo que a sidebar direita fique 100% livre e visível.
            wa_w = target_parent.width()
            pos_x = max(0, wa_w - 54 - drawer_w)

        self.drawer_container.setGeometry(pos_x, 0, drawer_w, sb_h)
        self.drawer_container.raise_()

    # ── Reordenação via Drag & Drop ───────────────────────────────────────

    def sync_panel_order_from_sidebar(self) -> None:
        """Sincroniza a ordem dos widgets de painéis no DrawerContentContainer com a sidebar."""
        order = self.sidebar.get_panel_order()
        for idx, pid in enumerate(order):
            self.drawer_container.reorder_panel(pid, idx)
        self.layout_order_changed.emit(order)
        logger.info(f"Gaveta '{self.side}': nova ordem de painéis: {order}")

    # ── Stroke Lock ───────────────────────────────────────────────────────

    def set_painting_state(self, is_painting: bool) -> None:
        """Chamado pelo CanvasWidget via sinais strokeStarted/strokeFinished."""
        self._is_painting = is_painting
        if is_painting and not self.is_pinned and self.is_open:
            self.close_drawer()
        if is_painting:
            # Garante que a pílula não expanda durante o traço
            self._expand_timer.stop()

    # ── Query e Persistência de Estado de Layout (ARCcC) ──────────────────

    def get_panel_order(self) -> List[str]:
        return self.sidebar.get_panel_order()

    @property
    def panel_data(self) -> Dict[str, dict]:
        return self._panels_info

    def get_state(self) -> dict:
        """Exporta o estado completo da doca lateral para persistência."""
        return {
            "is_open": self.is_open,
            "is_pinned": self.is_pinned,
            "active_panel_ids": list(self.active_panel_ids),
            "width": self.DRAWER_WIDTH,
            "panel_order": self.get_panel_order(),
        }

    def restore_state(self, state: dict) -> None:
        """Restaura o estado persistido da doca lateral."""
        if not state:
            return

        # 1. Ordem dos botões na sidebar
        order = state.get("panel_order", [])
        if order and hasattr(self.sidebar, "reorder_panels"):
            self.sidebar.reorder_panels(order)
            self.sync_panel_order_from_sidebar()

        # 2. Estado de fixação (Pin)
        is_pinned = state.get("is_pinned", False)
        self.set_pinned(is_pinned)

        # 3. Painéis ativos / Gaveta aberta
        active_ids = state.get("active_panel_ids", [])
        is_open = state.get("is_open", False)
        if is_open and active_ids:
            for pid in active_ids:
                if pid in self._panels_info and pid not in self.active_panel_ids:
                    self.toggle_panel(pid)
