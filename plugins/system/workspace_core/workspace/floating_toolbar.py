import logging
from typing import Dict, List, Optional
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.dialogs.floating_tool_window import FloatingToolWindow
from ui.core.icons import get_icon
from ui.core.state import ToolState
from ui.core.theme.manager import ThemeManager
from ui.core.tools import TOOL_META, DEFAULT_TOOLS
from .floating_toolbar_button import FloatingToolbarButton  # noqa: F401 (reexportado)

logger = logging.getLogger(__name__)


class FloatingToolbar(FloatingToolWindow):
    """Barra de ferramentas flutuante em formato de cápsula escura estilo Lumenia 2.0.

    View do ToolState: clicar num botão pede a troca ao estado; o destaque do
    botão muda quando o estado avisa (qualquer que seja a origem da troca).
    """

    drag_finished = QtCore.Signal(QtCore.QPoint)
    # Tamanho mudou (escala, animação de recolher/expandir): o workspace
    # reposiciona as barras. Até 2026-09-24 a barra procurava
    # `update_toolbar_position` no pai com `hasattr`.
    sizeChanged = QtCore.Signal()

    def __init__(self, tool_state: ToolState, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent, transparent_stylesheet=True)

        self._tool_state = tool_state
        self.dock_state: Optional[str] = "snapped_bottom"
        self.orientation = QtCore.Qt.Horizontal
        self._active_tool_id: str = tool_state.active_tool
        self.visible_tool_ids: List[str] = list(DEFAULT_TOOLS)
        self.auto_collapse_speed: str = "Rápido"
        self.buttons: Dict[str, FloatingToolbarButton] = {}

        self._drag_pos: Optional[QtCore.QPoint] = None
        self._geom_anim: Optional[QtCore.QVariantAnimation] = None
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
        tool_state.activeToolChanged.connect(self._on_active_tool_changed)

        # Conecta às alterações globais de tema, escala e idioma
        tm = ThemeManager.instance()
        tm.themeChanged.connect(self._apply_theme)  # método ligado: auto-desconecta
        tm.scaleChanged.connect(self._on_scale_changed)
        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

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

    def retranslate_ui(self) -> None:
        """Atualiza os tooltips de todas as ferramentas da barra flutuante."""
        for btn in self.buttons.values():
            btn.retranslate_ui()

    def _apply_theme(self) -> None:
        theme = ThemeManager.instance()
        bg_color, border_color = theme.get_color("bg_panel"), theme.get_color("border")
        fg_secondary, fg_primary = theme.get_color("text_sec"), theme.get_color("text_main")

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
            btn.clicked.connect(lambda _, t=tid: self._tool_state.set_active_tool(t))
            self.box_layout.addWidget(btn)
            self.buttons[tid] = btn

        self._show_active_tool(self._active_tool_id, animate=False)
        self._update_geometry(animate=False)

    def _on_active_tool_changed(self, tool_id: str, _previous: str) -> None:
        self._show_active_tool(tool_id, animate=False)

    def _show_active_tool(self, tool_id: str, animate: bool) -> None:
        """Destaca o botão da ferramenta ativa (só visual; o estado é do ToolState)."""
        self._active_tool_id = tool_id
        for tid, btn in self.buttons.items():
            btn.set_active(tid == tool_id)
        self._update_geometry(animate=animate)

    def _on_scale_changed(self, scale: float) -> None:
        """Propaga a escala global para botões, drag handle e dimensões da barra flutuante."""
        for btn in self.buttons.values():
            btn.update_scale(scale)
        h_thick = max(3, int(4 * scale))
        h_len = max(14, int(20 * scale))
        if self.orientation == QtCore.Qt.Vertical:
            self.drag_handle.setFixedSize(h_len, h_thick)
        else:
            self.drag_handle.setFixedSize(h_thick, h_len)
        self._update_geometry(animate=False)
        self.sizeChanged.emit()

    def set_orientation(self, orientation: QtCore.Qt.Orientation) -> None:
        """Alterna a orientação entre Horizontal e Vertical."""
        if self.orientation == orientation:
            return
        self.orientation = orientation
        s = ThemeManager.instance().ui_scale
        h_thick = max(3, int(4 * s))
        h_len = max(14, int(20 * s))
        if orientation == QtCore.Qt.Vertical:
            self.box_layout.setDirection(QtWidgets.QBoxLayout.TopToBottom)
            self.box_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
            self.drag_handle.setFixedSize(h_len, h_thick)
            self.box_layout.setContentsMargins(6, 10, 6, 10)
        else:
            self.box_layout.setDirection(QtWidgets.QBoxLayout.LeftToRight)
            self.box_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.drag_handle.setFixedSize(h_thick, h_len)
            self.box_layout.setContentsMargins(10, 6, 10, 6)

        self._update_geometry(animate=False)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._update_geometry(animate=False)

    def _update_geometry(self, animate: bool = True) -> None:
        count = 1 if self._is_collapsed else max(1, len(self.buttons))
        s = ThemeManager.instance().ui_scale
        btn_sz = max(24, int(38 * s))
        gap = max(3, int(6 * s))
        pad = max(6, int(10 * s))
        h_thick = max(3, int(4 * s))

        # Cálculo preciso do tamanho interno da cápsula ponderado pela escala
        inner_length = pad + h_thick + gap + (count * btn_sz) + max(0, (count - 1) * gap) + pad
        inner_breadth = max(36, int(52 * s))

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
            if self._geom_anim is not None and self._geom_anim.state() == QtCore.QAbstractAnimation.Running:
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

                self.sizeChanged.emit()

            def _on_anim_finish():
                self.container.setFixedSize(container_size)
                self.setMinimumSize(target_size)
                self.setMaximumSize(target_size)
                self.resize(target_size)
                if self._is_collapsed:
                    for tid, btn in self.buttons.items():
                        btn.setVisible(tid == self._active_tool_id)
                self.sizeChanged.emit()

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

    def set_auto_collapse_speed(self, speed: str) -> None:
        self.auto_collapse_speed = speed
        if speed == "Desativado":
            self._collapse_timer.stop()
            self._expand_timer.stop()
            self._do_expand()

    # ── Auto-Collapse (Hover & Timers) ───────────────────────────────────

    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        self._collapse_timer.stop()
        if self._is_collapsed:
            self._expand_timer.start(50)  # Always expand immediately on hover if collapsed
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._expand_timer.stop()
        speed_ms = self._get_speed_ms()
        if speed_ms > 0 and not self._is_collapsed:
            self._collapse_timer.start(speed_ms)
        super().leaveEvent(event)

    def _get_speed_ms(self) -> int:
        speeds = {"Desativado": 0, "Lento": 2000, "Ultra Rápido": 500}
        return speeds.get(self.auto_collapse_speed, 1000)

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

    # ── Métodos Canônicos de Persistência (ARCcC) ─────────────────────────

    def get_state(self) -> dict:
        """Exporta o estado atual completo da barra flutuante para persistência."""
        return {
            "dock_state": self.dock_state or "snapped_bottom",
            "pos_x": self.pos().x(),
            "pos_y": self.pos().y(),
            "orientation": "vertical" if self.orientation == QtCore.Qt.Vertical else "horizontal",
            "is_collapsed": self._is_collapsed,
            "visible_tools": list(self.visible_tool_ids),
            "auto_collapse_speed": self.auto_collapse_speed,
        }

    def restore_state(self, state: dict) -> None:
        """Restaura o estado persistido da barra flutuante."""
        if not state:
            return
        if "dock_state" in state:
            self.dock_state = state["dock_state"]
        if "orientation" in state:
            self.set_orientation(QtCore.Qt.Vertical if state["orientation"] == "vertical" else QtCore.Qt.Horizontal)
        if state.get("visible_tools"):
            self.visible_tool_ids = list(state["visible_tools"])
            self.rebuild_tools()
        if "auto_collapse_speed" in state:
            self.set_auto_collapse_speed(state["auto_collapse_speed"])
        if "is_collapsed" in state:
            self._is_collapsed = state["is_collapsed"]
            self._update_geometry(animate=False)
        if "pos_x" in state and "pos_y" in state and state.get("dock_state") in ("free", "free_floating", None):
            self.move(state["pos_x"], state["pos_y"])
