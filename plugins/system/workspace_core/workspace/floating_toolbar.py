import logging
from typing import Dict, List, Optional
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.icons import get_icon
from ui.core.theme.manager import ThemeManager
from ui.core.tools import TOOL_META, DEFAULT_TOOLS

logger = logging.getLogger(__name__)


class FloatingToolbarButton(QtWidgets.QPushButton):
    """Botão de ferramenta individual da barra flutuante (38x38px)."""

    def __init__(self, tool_id: str, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.tool_id = tool_id
        meta = TOOL_META.get(tool_id, {"name": tool_id.capitalize(), "icon": "brush"})
        self.tool_name = meta["name"]
        self.icon_key = meta["icon"]

        self.setFixedSize(38, 38)
        self.setIconSize(QtCore.QSize(22, 22))
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(self.tool_name)

        self._apply_style(active=False)

    def set_active(self, active: bool) -> None:
        self.setChecked(active)
        self._apply_style(active=active)

    def _apply_style(self, active: bool) -> None:
        theme = ThemeManager.instance()
        accent = theme.get_color("accent")
        bg_hover = theme.get_color("accent_muted")

        if active:
            self.setIcon(get_icon(self.icon_key, color="#ffffff"))
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent};
                    border: none;
                    border-radius: 8px;
                    padding: 0px;
                }}
            """)
        else:
            self.setIcon(get_icon(self.icon_key, color="text_main"))
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {bg_hover};
                }}
            """)


class FloatingToolbar(QtWidgets.QDialog):
    """
    Barra de ferramentas flutuante em formato de cápsula escura estilo Lumenia 2.0.
    
    Implementada como topo de janela nativa (Qt.Tool | Qt.FramelessWindowHint)
    com fundo translúcido para garantir 100% de imunidade a flickering sobre
    o viewport Surface WGPU.
    """

    drag_finished = QtCore.Signal(QtCore.QPoint)
    status_notification = QtCore.Signal(str)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("QDialog { background: transparent; border: none; }")

        self.dock_state: Optional[str] = "snapped_bottom"
        self.orientation = QtCore.Qt.Horizontal
        self._active_tool_id: str = "brush"
        self.visible_tool_ids: List[str] = list(DEFAULT_TOOLS)
        self.auto_collapse_speed: str = "Rápido"
        self.buttons: Dict[str, FloatingToolbarButton] = {}

        self._drag_pos: Optional[QtCore.QPoint] = None
        self._is_collapsed: bool = False

        # Timers de auto-recolhimento
        self._collapse_timer = QtCore.QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._do_collapse)

        self._expand_timer = QtCore.QTimer(self)
        self._expand_timer.setSingleShot(True)
        self._expand_timer.timeout.connect(self._do_expand)

        # Animações de redimensionamento
        self.anim_min = QtCore.QPropertyAnimation(self, b"minimumSize")
        self.anim_max = QtCore.QPropertyAnimation(self, b"maximumSize")
        self.anim_min.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.anim_max.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        self._build_ui()
        self._apply_theme()

        # Conecta às alterações globais de tema
        ThemeManager.instance().themeChanged.connect(lambda _: self._apply_theme())

    def _build_ui(self) -> None:
        self.main_layout = QtWidgets.QVBoxLayout(self)
        # Margem de 12px para renderização limpa da sombra e recuo transparente nativo
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(0)

        # Container interno da cápsula
        self.container = QtWidgets.QWidget(self)
        self.container.setObjectName("FloatBarContainer")

        # Efeito de sombra suave ajustado para os 12px de margem do layout
        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(shadow)

        self.main_layout.addWidget(self.container)

        # Layout da cápsula (Box)
        self.box_layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight, self.container)
        self.box_layout.setContentsMargins(10, 6, 10, 6)
        self.box_layout.setSpacing(6)
        self.box_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        # Pílula discreta de arrasto (Drag Handle visual)
        self.drag_handle = QtWidgets.QFrame(self.container)
        self.drag_handle.setObjectName("FloatBarDragHandle")
        self.drag_handle.setFixedSize(4, 20)
        self.drag_handle.setCursor(QtCore.Qt.SizeAllCursor)
        self.box_layout.addWidget(self.drag_handle, 0, QtCore.Qt.AlignCenter)

        self.rebuild_tools()

    def _apply_theme(self) -> None:
        theme = ThemeManager.instance()
        bg_color = theme.get_color("bg_panel")
        border_color = theme.get_color("border")
        fg_secondary = theme.get_color("text_sec")
        fg_primary = theme.get_color("text_main")

        self.container.setStyleSheet(f"""
            QWidget#FloatBarContainer {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QFrame#FloatBarDragHandle {{
                background-color: {fg_secondary};
                border-radius: 2px;
            }}
            QFrame#FloatBarDragHandle:hover {{
                background-color: {fg_primary};
            }}
        """)

        # Atualiza a estilização de cada botão
        for tid, btn in self.buttons.items():
            btn._apply_style(active=(tid == self._active_tool_id))

    def rebuild_tools(self) -> None:
        """Reconstrói os botões da barra flutuante de acordo com a lista de visibilidade."""
        for btn in list(self.buttons.values()):
            self.box_layout.removeWidget(btn)
            btn.hide()
            btn.setParent(None)
            btn.deleteLater()
        self.buttons.clear()

        for tid in self.visible_tool_ids:
            if tid not in TOOL_META:
                continue
            btn = FloatingToolbarButton(tid, self.container)
            btn.clicked.connect(lambda _, t=tid: self.select_tool(t))
            self.box_layout.addWidget(btn)
            self.buttons[tid] = btn

        self.select_tool(self._active_tool_id, notify=False)
        self._update_geometry(animate=False)

    def select_tool(self, tool_id: str, notify: bool = True, animate: bool = False) -> None:
        """Marca a ferramenta selecionada e notifica caso não tenha backend implementado."""
        if tool_id not in TOOL_META:
            return

        if getattr(self, "_is_selecting_tool", False):
            return

        self._is_selecting_tool = True
        try:
            self._active_tool_id = tool_id
            meta = TOOL_META[tool_id]

            for tid, btn in self.buttons.items():
                btn.set_active(tid == tool_id)

            # Repassa seleção de ferramentas ao workspace sem gerar loop de chamadas
            parent_ws = getattr(self, "_workspace", None) or self.parentWidget()
            if parent_ws and hasattr(parent_ws, "select_tool"):
                if getattr(parent_ws, "_current_tool", None) != tool_id:
                    parent_ws.select_tool(tool_id)

            if notify:
                if meta["implemented"]:
                    self.status_notification.emit(f"Ferramenta ativa: {meta['name']}")
                else:
                    self.status_notification.emit(f"Ferramenta '{meta['name']}' em desenvolvimento.")

            self._update_geometry(animate=animate)
        finally:
            self._is_selecting_tool = False

    def set_orientation(self, orientation: QtCore.Qt.Orientation) -> None:
        """Alterna a orientação entre Horizontal e Vertical."""
        if self.orientation == orientation:
            return
        self.orientation = orientation

        if orientation == QtCore.Qt.Vertical:
            self.box_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
            self.box_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
            self.drag_handle.setFixedSize(20, 4)
            self.box_layout.setContentsMargins(6, 10, 6, 10)
        else:
            self.box_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)
            self.box_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.drag_handle.setFixedSize(4, 20)
            self.box_layout.setContentsMargins(10, 6, 10, 6)

        self._update_geometry(animate=False)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._update_geometry(animate=False)

    def _update_geometry(self, animate: bool = True) -> None:
        count = 1 if self._is_collapsed else max(1, len(self.buttons))

        # Cálculo preciso do tamanho interno da cápsula
        inner_length = 10 + 4 + 6 + (count * 38) + max(0, (count - 1) * 6) + 10
        inner_breadth = 52

        container_size = (
            QtCore.QSize(inner_length, inner_breadth)
            if self.orientation == QtCore.Qt.Horizontal
            else QtCore.QSize(inner_breadth, inner_length)
        )

        # O tamanho da janela nativa QDialog inclui a margem de 12px de cada lado (24px total)
        window_w = inner_length + 24
        window_h = inner_breadth + 24

        target_size = (
            QtCore.QSize(window_w, window_h)
            if self.orientation == QtCore.Qt.Horizontal
            else QtCore.QSize(window_h, window_w)
        )

        if animate and self.isVisible():
            if hasattr(self, "_geom_anim") and self._geom_anim.state() == QtCore.QAbstractAnimation.Running:
                self._geom_anim.stop()

            start_c_size = self.container.size()
            start_w_size = self.size()

            self._geom_anim = QtCore.QVariantAnimation(self)
            self._geom_anim.setDuration(220)
            self._geom_anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            self._geom_anim.setStartValue(0.0)
            self._geom_anim.setEndValue(1.0)

            # Na expansão, exibe todos os botões imediatamente para fluidez
            if not self._is_collapsed:
                for btn in self.buttons.values():
                    btn.setVisible(True)

            def _on_anim_step(progress: float):
                # Interpola o tamanho do container interno
                cw = int(start_c_size.width() + (container_size.width() - start_c_size.width()) * progress)
                ch = int(start_c_size.height() + (container_size.height() - start_c_size.height()) * progress)
                self.container.setFixedSize(cw, ch)

                # Interpola o tamanho da janela externa
                ww = int(start_w_size.width() + (target_size.width() - start_w_size.width()) * progress)
                wh = int(start_w_size.height() + (target_size.height() - start_w_size.height()) * progress)
                self.setMinimumSize(ww, wh)
                self.setMaximumSize(ww, wh)
                self.resize(ww, wh)

                parent_ws = getattr(self, "_workspace", None) or self.parentWidget()
                if parent_ws and hasattr(parent_ws, "update_toolbar_position"):
                    parent_ws.update_toolbar_position()

            def _on_anim_finish():
                self.container.setFixedSize(container_size)
                self.setMinimumSize(target_size)
                self.setMaximumSize(target_size)
                self.resize(target_size)
                if self._is_collapsed:
                    for tid, btn in self.buttons.items():
                        btn.setVisible(tid == self._active_tool_id)
                parent_ws = getattr(self, "_workspace", None) or self.parentWidget()
                if parent_ws and hasattr(parent_ws, "update_toolbar_position"):
                    parent_ws.update_toolbar_position()

            self._geom_anim.valueChanged.connect(_on_anim_step)
            self._geom_anim.finished.connect(_on_anim_finish)
            self._geom_anim.start()
        else:
            for tid, btn in self.buttons.items():
                if self._is_collapsed:
                    btn.setVisible(tid == self._active_tool_id)
                else:
                    btn.setVisible(True)
            self.container.setFixedSize(container_size)
            self.setMinimumSize(target_size)
            self.setMaximumSize(target_size)
            self.resize(target_size)

    # ── Auto-Collapse (Hover & Timers) ───────────────────────────────────

    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        self._collapse_timer.stop()
        speed_ms = self._get_speed_ms()
        if speed_ms > 0 and self._is_collapsed:
            self._expand_timer.start(100)  # Intent de 100ms no hover
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._expand_timer.stop()
        speed_ms = self._get_speed_ms()
        if speed_ms > 0 and not self._is_collapsed:
            self._collapse_timer.start(speed_ms)
        super().leaveEvent(event)

    def _get_speed_ms(self) -> int:
        preset = self.auto_collapse_speed
        if preset == "Desativado":
            return 0
        if preset == "Lento":
            return 2000
        if preset == "Ultra Rápido":
            return 500
        return 1000  # Rápido

    def _do_collapse(self) -> None:
        self._is_collapsed = True
        self._update_geometry(animate=True)

    def _do_expand(self) -> None:
        self._is_collapsed = False
        self._update_geometry(animate=True)

    # ── Drag Handle & Mouse Events ───────────────────────────────────────

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_pos and event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_pos:
            self._drag_pos = None
            self.drag_finished.emit(self.pos())
        super().mouseReleaseEvent(event)
