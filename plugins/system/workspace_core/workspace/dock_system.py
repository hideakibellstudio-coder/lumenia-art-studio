"""
AdvancedDockSystem — Sistema de Gavetas Dinâmicas com Auto-Recolhimento
=======================================================================
Implementa gavetas laterais com:
  - Auto-recolhimento da sidebar (54px → 0px) via QPropertyAnimation configurável
  - PillHandle flutuante para reativar a sidebar recolhida
  - Gaveta flutuante (unpinned) ou colada no layout (pinned)
  - Empilhamento acumulativo de painéis
  - Spacer dinâmico baseado na política de tamanho dos painéis
  - Drag & Drop de reordenação de botões da sidebar com threshold anti-jitter (caneta)
  - Blindagem RuntimeError para descarregamento dinâmico de plugins
  - Suspensão durante pintura (Stroke Lock)

REGRA WGPU: Nenhum widget filho pode flutuar sobre o CanvasWidget (HWND separado).
A PillHandle e o DrawerContentContainer (unpinned) são filhos do workspace_area,
que é um QWidget comum que "abraça" o canvas sem tocá-lo.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.logger import get_logger

if TYPE_CHECKING:
    from plugins.system.workspace_core.workspace.workspace_container import WorkspaceContainer

logger = get_logger("Workspace.DockSystem")


# ── Configurações de velocidade / delay ────────────────────────────────────

SPEED_MAP = {
    "Ultra Rápido": 60,
    "Rápido":       180,
    "Normal":       320,
    "Lento":        500,
}

DELAY_MAP = {
    "Sem Atraso":      0,
    "Curto (100ms)":   100,
    "Normal (350ms)":  350,
    "Longo (800ms)":   800,
}


# ── 1. BOTÃO DA SIDEBAR DE ÍCONES (54px) ──────────────────────────────────

class SidebarButton(QtWidgets.QToolButton):
    """Botão de ícone da sidebar com suporte a drag & drop de reordenação."""

    def __init__(
        self,
        panel_id: str,
        title: str,
        icon_path: str | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.panel_id = panel_id
        self.setCheckable(True)
        self.setFixedSize(44, 44)
        self.setToolTip(title)

        if icon_path and QtCore.QFile.exists(icon_path):
            self.setIcon(QtGui.QIcon(icon_path))
            self.setIconSize(QtCore.QSize(22, 22))
        else:
            self.setText(title[0].upper() if title else "?")

        self.setCursor(QtCore.Qt.PointingHandCursor)

        # Estado para drag & drop com threshold (anti-jitter caneta Stylus)
        self._drag_start_pos: QtCore.QPoint | None = None

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_normal = theme.get_color("bg_panel")
        bg_hover  = theme.get_color("accent_muted")
        bg_active = theme.get_color("accent")
        text_main = theme.get_color("text_main")
        border    = theme.get_color("border")

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg_normal};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }}
            QToolButton:hover {{
                background-color: {bg_hover};
                border-color: {bg_active};
            }}
            QToolButton:checked {{
                background-color: {bg_active};
                color: #ffffff;
                border: 1px solid {bg_active};
            }}
        """)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if (
            event.buttons() & QtCore.Qt.LeftButton
            and self._drag_start_pos is not None
        ):
            delta = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if delta >= QtWidgets.QApplication.startDragDistance():
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def _start_drag(self) -> None:
        """Inicia o drag & drop com MIME type próprio do Lumenia."""
        self._drag_start_pos = None
        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setData("application/x-lumenia-panel", self.panel_id.encode("utf-8"))
        drag.setMimeData(mime)

        # Pixmap preview do botão
        pix = self.grab()
        drag.setPixmap(pix)
        drag.setHotSpot(pix.rect().center())
        drag.exec(QtCore.Qt.MoveAction)


# ── 2. SIDEBAR DE ÍCONES (Animável 54px ↔ 0px) ────────────────────────────

class SidebarWidget(QtWidgets.QWidget):
    """Sidebar de ícones vertical animável (0px ↔ 54px) na borda externa."""

    button_clicked = QtCore.Signal(str)  # panel_id

    def __init__(self, side: str = "left", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.side = side

        # Dimensões animáveis (não usar setFixedWidth — impede QPropertyAnimation)
        self.setMinimumWidth(0)
        self.setMaximumWidth(54)

        self.setAcceptDrops(True)

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(5, 8, 5, 8)
        self._layout.setSpacing(6)
        self._layout.setAlignment(QtCore.Qt.AlignTop)

        self._buttons: Dict[str, SidebarButton] = {}

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border   = theme.get_color("border",   "#2e2e38")

        border_side = "border-right" if self.side == "left" else "border-left"
        self.setStyleSheet(f"""
            SidebarWidget {{
                background-color: {bg_panel};
                {border_side}: 1px solid {border};
                border-top: 1px solid {border};
                border-bottom: 1px solid {border};
            }}
        """)


    def add_panel_button(self, panel_id: str, title: str, icon_path: str | None = None) -> SidebarButton:
        if panel_id in self._buttons:
            return self._buttons[panel_id]
        btn = SidebarButton(panel_id, title, icon_path, self)
        btn.clicked.connect(lambda: self.button_clicked.emit(panel_id))
        self._buttons[panel_id] = btn
        self._layout.addWidget(btn)
        return btn

    def remove_panel_button(self, panel_id: str) -> None:
        btn = self._buttons.pop(panel_id, None)
        if btn:
            try:
                self._layout.removeWidget(btn)
                btn.deleteLater()
            except RuntimeError:
                pass

    def set_button_active(self, panel_id: str, active: bool) -> None:
        btn = self._buttons.get(panel_id)
        if btn:
            try:
                btn.blockSignals(True)
                btn.setChecked(active)
                btn.blockSignals(False)
            except RuntimeError:
                pass

    def get_panel_order(self) -> List[str]:
        """Retorna a lista de panel_ids na ordem visual dos botões."""
        order = []
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), "panel_id"):
                order.append(item.widget().panel_id)
        return order

    # ── Drag & Drop ────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasFormat("application/x-lumenia-panel"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if event.mimeData().hasFormat("application/x-lumenia-panel"):
            event.acceptProposedAction()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if not event.mimeData().hasFormat("application/x-lumenia-panel"):
            event.ignore()
            return

        pid = event.mimeData().data("application/x-lumenia-panel").data().decode("utf-8")
        btn = self._buttons.get(pid)
        if not btn:
            event.ignore()
            return

        # Calcula a posição de inserção pelo centro dos botões
        drop_y    = event.position().toPoint().y()
        target_idx = self._layout.count()  # padrão: final
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if not item or not item.widget():
                continue
            w = item.widget()
            center_y = w.y() + w.height() // 2
            if drop_y < center_y:
                target_idx = i
                break

        self._layout.removeWidget(btn)
        self._layout.insertWidget(target_idx, btn)
        event.acceptProposedAction()

        logger.info(f"Sidebar '{self.side}': reordenou '{pid}' para índice {target_idx}")


# ── 3. CABEÇALHO DA GAVETA ─────────────────────────────────────────────────

class DrawerHeader(QtWidgets.QWidget):
    """Barra superior da gaveta (Título + Botão Pin 📌)."""

    pin_toggled = QtCore.Signal(bool)

    def __init__(self, title: str = "", side: str = "left", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.side = side
        self.setFixedHeight(34)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        self.title_label = QtWidgets.QLabel(title.upper(), self)

        self.btn_pin = QtWidgets.QToolButton(self)
        self.btn_pin.setCheckable(True)
        self.btn_pin.setToolTip("Fixar Doca no Layout (Pin)")
        self.btn_pin.setFixedSize(24, 24)
        self.btn_pin.setText("📌")
        self.btn_pin.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_pin.toggled.connect(self.pin_toggled)

        if self.side == "left":
            # Gaveta Esquerda: Stretch no lado esquerdo (externo) -> Título -> Pin (na borda direita/interna)
            self.title_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            layout.addStretch()
            layout.addWidget(self.title_label)
            layout.addWidget(self.btn_pin)
        else:
            # Gaveta Direita: Pin (na borda esquerda/interna) -> Título -> Stretch no lado direito (externo)
            self.title_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            layout.addWidget(self.btn_pin)
            layout.addWidget(self.title_label)
            layout.addStretch()


        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def set_title(self, title: str) -> None:
        self.title_label.setText(title.upper())

    def set_pinned(self, pinned: bool) -> None:
        self.btn_pin.blockSignals(True)
        self.btn_pin.setChecked(pinned)
        self.btn_pin.blockSignals(False)

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_header = theme.get_color("bg_panel", "#1e1e24")
        text_main = theme.get_color("text_main", "#f3f4f6")
        border    = theme.get_color("border",    "#2e2e38")

        c = QtGui.QColor(bg_header)
        p = self.palette()
        p.setColor(QtGui.QPalette.Window, c)
        p.setColor(QtGui.QPalette.Base, c)
        self.setPalette(p)

        self.title_label.setStyleSheet(
            f"color: {text_main}; font-weight: bold; font-size: 11px; "
            "background-color: transparent; border: none;"
        )
        self.setStyleSheet(f"""
            DrawerHeader {{
                background-color: {bg_header};
                border-bottom: 1px solid {border};
            }}
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                color: {text_main};
                font-size: 11px;
            }}
            QToolButton:hover {{
                background-color: rgba(150, 150, 150, 0.15);
            }}
            QToolButton:checked {{
                background-color: rgba(99, 102, 241, 0.3);
            }}
        """)


# ── 4. CONTAINER DE CONTEÚDO DA GAVETA ────────────────────────────────────

class DrawerContentContainer(QtWidgets.QWidget):
    """Contêiner físico do conteúdo da gaveta com suporte a empilhamento."""

    def __init__(self, side: str = "left", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.side = side
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)  # Inicia recolhida a 0px (animável)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = DrawerHeader("", side=side, parent=self)
        layout.addWidget(self.header)

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.scroll_content = QtWidgets.QWidget()
        self.scroll_content.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.panels_layout   = QtWidgets.QVBoxLayout(self.scroll_content)
        self.panels_layout.setContentsMargins(0, 0, 0, 0)
        self.panels_layout.setSpacing(0)

        self.spacer = QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        self.spacer_added = True
        self.panels_layout.addItem(self.spacer)

        if self.scroll_area.viewport():
            self.scroll_area.viewport().setAttribute(QtCore.Qt.WA_StyledBackground, True)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

        self._panels: Dict[str, QtWidgets.QWidget] = {}

        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()
        self.ensurePolished()

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border   = theme.get_color("border",   "#2e2e38")

        # Ajusta QPalette nativa dos componentes internos para evitar o flash branco do Qt no 1º frame
        c = QtGui.QColor(bg_panel)
        for w in (self, self.scroll_area, self.scroll_area.viewport(), self.scroll_content):
            if w:
                p = w.palette()
                p.setColor(QtGui.QPalette.Window, c)
                p.setColor(QtGui.QPalette.Base, c)
                w.setPalette(p)

        border_side = "border-right" if self.side == "left" else "border-left"
        self.setStyleSheet(f"""
            DrawerContentContainer {{
                background-color: {bg_panel};
                {border_side}: 1px solid {border};
            }}
            QScrollArea, QScrollArea > QWidget > QWidget {{
                background-color: {bg_panel};
                border: none;
            }}
        """)

    def add_panel_widget(self, panel_id: str, title: str, widget: QtWidgets.QWidget) -> None:
        if panel_id in self._panels:
            return
        self._panels[panel_id] = widget
        # Insere antes do spacer
        insert_at = max(0, self.panels_layout.count() - (1 if self.spacer_added else 0))
        self.panels_layout.insertWidget(insert_at, widget)
        widget.hide()

    def remove_panel_widget(self, panel_id: str) -> None:
        widget = self._panels.pop(panel_id, None)
        if widget:
            try:
                self.panels_layout.removeWidget(widget)
                widget.deleteLater()
            except RuntimeError:
                pass

    def reorder_panel(self, panel_id: str, new_index: int) -> None:
        """Reposiciona o widget de um painel no layout para refletir a ordem da sidebar."""
        widget = self._panels.get(panel_id)
        if not widget:
            return
        try:
            self.panels_layout.removeWidget(widget)
            self.panels_layout.insertWidget(new_index, widget)
        except RuntimeError:
            pass

    def update_spacer(self, active_panel_ids: Set[str]) -> None:
        """Adiciona/remove o spacer de acordo com a política de tamanho dos painéis visíveis."""
        has_expanding = False
        for pid, widget in self._panels.items():
            if pid not in active_panel_ids:
                continue
            try:
                policy = widget.sizePolicy().verticalPolicy()
                if policy in (QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding):
                    has_expanding = True
                    break
            except RuntimeError:
                continue

        if self.spacer_added:
            self.panels_layout.removeItem(self.spacer)
            self.spacer_added = False

        if not has_expanding:
            self.panels_layout.addItem(self.spacer)
            self.spacer_added = True


# ── 5. ADVANCED DOCK SYSTEM (Orquestrador Principal) ──────────────────────

class AdvancedDockSystem(QtWidgets.QWidget):
    """
    Gerenciador da Doca Lateral (Esquerda ou Direita).

    Funcionalidades:
      - Sidebar animável (54px ↔ 0px) com auto-recolhimento configurável
      - PillHandle flutuante para reabrir quando a sidebar está recolhida
      - Gaveta flutuante (unpinned) ou inline no layout (pinned)
      - Empilhamento acumulativo de painéis com spacer dinâmico
      - Drag & Drop de reordenação de botões
      - Blindagem RuntimeError para descarregamento dinâmico de plugins
      - Stroke Lock: fecha gaveta ao iniciar traço no canvas
    """

    drawer_opened = QtCore.Signal(str)   # panel_id ou "stacked"
    drawer_closed = QtCore.Signal()
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

        # ── Inserção no layout ─────────────────────────────────────────
        self._outer_layout.addWidget(self.sidebar)
        self.drawer_container.hide()

        # ── PillHandle (injetado posteriormente pelo WorkspaceContainer) ──
        self._pill: object = None  # Referência à PillHandle

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
            # Se auto_collapse ou pin estiver ativo e o mouse não está sobre a sidebar, recolhe imediatamente
            if not self.sidebar.underMouse() and (not self.is_open or self.is_pinned):
                self._do_collapse()
        else:
            # Desligou auto-recolhimento e não está pinada → expande se estiver colapsada
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
        current = self.sidebar.maximumWidth()
        if current == 0:
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
        current = self.sidebar.maximumWidth()
        if current == self.SIDEBAR_EXPANDED and self.sidebar.width() == self.SIDEBAR_EXPANDED and not self.sidebar.isHidden():
            return
        self._sidebar_anim.stop()
        self._sidebar_anim.setStartValue(current)
        self._sidebar_anim.setEndValue(self.SIDEBAR_EXPANDED)
        self._sidebar_anim.start()

    def _on_sidebar_anim_value_changed(self, value: int) -> None:
        self.sidebar.setMinimumWidth(value)
        if hasattr(self._workspace, "_update_pill_positions"):
            self._workspace._update_pill_positions()

    def _on_sidebar_anim_finished(self) -> None:
        """Quando a sidebar terminar de recolher, exibe a pílula."""
        if self.sidebar.maximumWidth() == 0:
            self.sidebar.hide()
            self._show_pill()
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
        # Recolhe em dois cenários (igual ao legado):
        #   1. Auto-collapse ativo (sidebar recolhe por inatividade)
        #   2. is_pinned ativo (sidebar recua para dar espaço ao painel inline)
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
            self.drawer_container.header.set_title("PAINÉIS EMPILHADOS")
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
        # Ao pinar: sidebar recolhe imediatamente (igual ao legado toggle_pin)
        # para dar espaço ao painel agora fixo no layout.
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
            self.drawer_container.setParent(self)
            if self.side == "left":
                self._outer_layout.insertWidget(1, self.drawer_container)
            else:
                self._outer_layout.insertWidget(0, self.drawer_container)
        else:
            self._outer_layout.removeWidget(self.drawer_container)
            self.drawer_container.setParent(target_parent)

        self.open_drawer_anim()

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

    # ── Query de estado de layout ─────────────────────────────────────────

    def get_panel_order(self) -> List[str]:
        return self.sidebar.get_panel_order()

    @property
    def panel_data(self) -> Dict[str, dict]:
        return self._panels_info
