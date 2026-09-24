"""
LayersPanel — painel de camadas do Lumenia
===========================================
View do `LocalLayerManager` do documento ativo: árvore de camadas,
opacidade/modo de mesclagem da camada ativa, barras de ações e papel.

Contrato (desde 2026-09-24):
- O painel NÃO sincroniza o motor. Toda alteração passa pelo
  `LocalLayerManager` (fonte única), direto ou via `LayerModel.setData`, e o
  gerenciador sincroniza o motor e emite os sinais que atualizam a view.
- Comandos (adicionar, excluir, mover, travas...) moram em
  `ui.core.document.layer_commands.LayerCommands` (os mesmos do menu Camada);
  o fluxo de camada de ajuste com prévia, em `FilterLayerFlow`. Ambos têm
  estado próprio e não mexem em atributos deste painel.
- Mensagens de status saem pelo sinal `statusMessage`; quem liga é o plugin
  (antes o painel procurava a janela ativa e o `statusBar()` dela).
- Os métodos públicos abaixo de "API das barras" são o contrato usado por
  `grid.py` (LayersPrimaryBox/LayersSecondaryBar) e pelos atalhos da view.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QItemSelectionModel, QRect, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from ui.core.document.layer_blend_mode import LayerBlendMode
from ui.core.document.layer_commands import LayerCommands
from ui.core.document.layer_manager import LocalLayerManager
from ui.core.engine.registry import EngineRegistry
from ui.core.widgets.card_box import PanelCardBox

from .delegate import LayerItemDelegate
from .filter_layer_flow import FilterLayerFlow
from .grid import LayersPrimaryBox, LayersSecondaryBar
from .header import LayersHeader
from .model import ROLE_COLLAPSED, ROLE_UID, LayerModel
from .panel_rename_popup import LayerRenamePopup
from .paper import PaperLayerWidget
from .view import LayerTreeView

logger = logging.getLogger(__name__)

_THUMB_W, _THUMB_H = 38, 28


class LayersPanel(QWidget):
    """Widget principal do Painel de Camadas."""

    statusMessage = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Sem documento até o workspace chamar set_layer_manager(...): o
        # painel não cria um gerenciador próprio (widget não é dono de estado).
        self.layer_manager: Optional[LocalLayerManager] = None
        # True enquanto o painel mexe na seleção da árvore ou o modelo Qt se
        # reconstrói; impede que isso volte ao gerenciador como "usuário
        # escolheu outra camada".
        self._syncing_view = False

        self._commands = LayerCommands(self.show_status, lambda: self.layer_manager)
        self._filters = FilterLayerFlow(self, self.show_status)

        self._build_ui()
        self.set_layer_manager(None)

        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme("")

    # ── Documento ─────────────────────────────────────────────────────────

    def set_layer_manager(self, manager: Optional[LocalLayerManager]) -> None:
        if self.layer_manager is not None:
            self.layer_manager.active_layer_changed.disconnect(self._on_active_layer_changed)
            self.layer_manager.layer_property_changed.disconnect(self._sync_header_controls)
            self.layer_manager.layer_added.disconnect(self._on_layer_added)
            self.layer_manager.thumbnail_updated.disconnect(self._refresh_thumbnail)

        self.layer_manager = manager
        self._filters.layer_manager = manager
        self.model.set_manager(manager)

        enabled = manager is not None
        for widget in (self.view, self.header, self.secondary_bar, self.paper_widget, self.primary_box):
            widget.setEnabled(enabled)
        if manager is None:
            return

        manager.active_layer_changed.connect(self._on_active_layer_changed)
        manager.layer_property_changed.connect(self._sync_header_controls)
        manager.layer_added.connect(self._on_layer_added)
        manager.thumbnail_updated.connect(self._refresh_thumbnail)
        self._sync_header_controls()
        self._show_active_in_view()

    # ── API das barras (grid.py) e dos atalhos da view ────────────────────

    def add_layer(self, name=None):
        self._commands.add_layer(name)

    def add_group(self, name=None):
        self._commands.add_group(name)

    def add_filter_layer(self, _filter_type=None):
        self._filters.add_filter_layer()

    def open_edit_filter_popup(self, uid: Optional[int] = None):
        target = uid if uid is not None else self._active_uid()
        if target is not None:
            self._filters.edit_filter(target)

    def delete_selection(self):
        self._commands.delete_active()

    def duplicate_layer(self):
        self._commands.duplicate_active()

    def merge_down(self):
        self._commands.merge_active_down()

    def move_up(self):
        self._commands.move_active_up()

    def move_down(self):
        self._commands.move_active_down()

    def grid_clear(self):
        self._commands.clear_active_pixels()

    def grid_toggle_lock(self):
        self._toggle_active(self._commands.toggle_lock)

    def grid_toggle_alpha(self):
        self._toggle_active(self._commands.toggle_alpha_lock)

    def grid_toggle_clip(self):
        self._toggle_active(self._commands.toggle_clipping_mask)

    def open_rename_popup(self, uid: int, rect: QRect):
        layer = self.layer_manager.get_layer_by_uid(uid) if self.layer_manager else None
        if layer is None:
            return
        global_pos = self.view.viewport().mapToGlobal(rect.topLeft())
        target_rect = QRect(global_pos.x() + 85, global_pos.y() + 4, max(150, rect.width() - 95), 28)
        popup = LayerRenamePopup(layer.name, target_rect, self)
        popup.name_changed.connect(lambda name: self._commands.rename(uid, name))
        popup.show()
        popup.input_edit.setFocus()

    def show_status(self, message: str) -> None:
        logger.info("[Layers] %s", message)
        self.statusMessage.emit(message)

    # ── Ações vindas da árvore e do cabeçalho ─────────────────────────────

    def _on_delegate_action(self, action_type: str, uid: int) -> None:
        if action_type == "toggle_visibility":
            self._commands.toggle_visibility(uid)
        elif action_type == "toggle_lock":
            self._commands.toggle_lock(uid)
        elif action_type == "toggle_alpha":
            self._commands.toggle_alpha_lock(uid)
        elif action_type == "toggle_clipping_mask":
            self._commands.toggle_clipping_mask(uid)
        elif action_type == "toggle_collapse":
            index = self.model.find_index_by_uid(uid)
            if index.isValid():
                is_expanded = self.view.isExpanded(index)
                self.view.setExpanded(index, not is_expanded)
                self.model.setData(index, is_expanded, ROLE_COLLAPSED)
        elif action_type == "edit_filter":
            self.open_edit_filter_popup(uid)

    def _on_ui_opacity_changed(self, value: int) -> None:
        if not self._syncing_view and self.layer_manager is not None:
            self._commands.set_active_opacity(value / 100.0)

    def _on_ui_blend_changed(self, label) -> None:
        # O combo emite o rótulo; o documento guarda sempre o enum canônico.
        if not self._syncing_view and self.layer_manager is not None:
            self._commands.set_active_blend_mode(LayerBlendMode.from_label(label))

    def _toggle_active(self, command) -> None:
        uid = self._active_uid()
        if uid is not None:
            command(uid)

    def _active_uid(self) -> Optional[int]:
        layer = self.layer_manager.get_active_layer() if self.layer_manager else None
        return layer.uid if layer else None

    # ── Sincronia árvore ↔ camada ativa (só visual) ───────────────────────

    def _on_view_selection_changed(self, _selected=None, _deselected=None) -> None:
        if self._syncing_view or self.model.is_modifying_structure or self.layer_manager is None:
            return
        indexes = self.view.selectionModel().selectedIndexes()
        uid = indexes[0].data(ROLE_UID) if indexes else None
        if uid:
            self.layer_manager.set_active_layer(uid)

    def _on_active_layer_changed(self, _uid) -> None:
        self._sync_header_controls()
        self._show_active_in_view()

    def _on_model_about_to_rebuild(self) -> None:
        self._syncing_view = True

    def _on_model_rebuilt(self) -> None:
        self._syncing_view = False
        self._show_active_in_view()

    def _show_active_in_view(self) -> None:
        uid = self._active_uid()
        index = self.model.find_index_by_uid(uid) if uid is not None else self.model.index(0, 0)
        if not index.isValid():
            return
        self._syncing_view = True
        try:
            self.view.setCurrentIndex(index)
            self.view.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)
            self.view.scrollTo(index)
        finally:
            self._syncing_view = False

    def _sync_header_controls(self, *_args) -> None:
        layer = self.layer_manager.get_active_layer() if self.layer_manager else None
        if layer is None:
            return
        self._syncing_view = True
        try:
            self.header.set_values(int(layer.opacity * 100), layer.blend_mode, layer.is_group)
        finally:
            self._syncing_view = False

    def _on_layer_added(self, layer) -> None:
        # Camada nova ou duplicada: a miniatura vem dos pixels reais do motor.
        self._refresh_thumbnail(layer.uid)

    def _refresh_thumbnail(self, uid: int) -> None:
        """Lê a miniatura real da camada no motor e atualiza o item da árvore."""
        backend = EngineRegistry.instance().get_backend()
        layer = self.layer_manager.get_layer_by_uid(uid) if self.layer_manager else None
        if backend is None or layer is None:
            return
        raw = backend.get_layer_thumbnail_buffer(self.layer_manager.layers.index(layer), _THUMB_W, _THUMB_H)
        if not raw:
            return
        from PySide6.QtGui import QImage, QPixmap

        image = QImage(raw, _THUMB_W, _THUMB_H, _THUMB_W * 4, QImage.Format_RGBA8888)
        if not image.isNull():
            layer.thumb = QPixmap.fromImage(image)
            index = self.model.find_index_by_uid(uid)
            if index.isValid():
                self.model.dataChanged.emit(index, index)

    # ── Construção ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(240)

        content_inner = QWidget()
        ci_layout = QVBoxLayout(content_inner)
        ci_layout.setContentsMargins(4, 4, 4, 4)
        ci_layout.setSpacing(4)

        self.header = LayersHeader()
        self.header.opacityChanged.connect(self._on_ui_opacity_changed)
        self.header.blendModeChanged.connect(self._on_ui_blend_changed)
        ci_layout.addWidget(self.header)

        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.secondary_bar = LayersSecondaryBar(self)
        left_layout.addWidget(self.secondary_bar)

        self.model = LayerModel(None)
        self.model.statusMessage.connect(self.show_status)
        self.model.modelAboutToBeReset.connect(self._on_model_about_to_rebuild)
        self.model.modelReset.connect(self._on_model_rebuilt)
        self.model.layoutAboutToBeChanged.connect(self._on_model_about_to_rebuild)
        self.model.layoutChanged.connect(self._on_model_rebuilt)

        self.view = LayerTreeView()
        self.view.setModel(self.model)
        self.view.setMinimumHeight(150)
        self.delegate = LayerItemDelegate()
        self.view.setItemDelegate(self.delegate)
        self.view.selectionModel().selectionChanged.connect(self._on_view_selection_changed)
        self.delegate.actionRequested.connect(self._on_delegate_action)

        self.view.deleteRequested.connect(self.delete_selection)
        self.view.moveUpRequested.connect(self.move_up)
        self.view.moveDownRequested.connect(self.move_down)
        self.view.mergeDownRequested.connect(self.merge_down)
        self.view.duplicateRequested.connect(self.duplicate_layer)
        self.view.clearRequested.connect(self.grid_clear)
        self.view.addLayerRequested.connect(self.add_layer)
        self.view.addGroupRequested.connect(self.add_group)
        self.view.toggleClippingRequested.connect(self._commands.toggle_clipping_mask)
        self.view.editFilterRequested.connect(self.open_edit_filter_popup)
        self.view.renameRequested.connect(self.open_rename_popup)
        left_layout.addWidget(self.view)

        self.paper_widget = PaperLayerWidget(None)
        left_layout.addWidget(self.paper_widget)
        bottom_layout.addWidget(left_widget)

        self.v_divider = QFrame()
        self.v_divider.setFrameShape(QFrame.VLine)
        self.v_divider.setFrameShadow(QFrame.Plain)
        self.v_divider.setFixedWidth(1)
        bottom_layout.addWidget(self.v_divider)

        right_panel = QWidget()
        right_panel.setFixedWidth(42)
        r_lay_outer = QVBoxLayout(right_panel)
        r_lay_outer.setContentsMargins(4, 6, 4, 8)
        r_lay_outer.setAlignment(Qt.AlignTop)
        self.primary_box = LayersPrimaryBox(self)
        self.primary_box.setObjectName("PrimaryBox")
        r_lay_outer.addWidget(self.primary_box)
        r_lay_outer.addStretch()
        bottom_layout.addWidget(right_panel)
        ci_layout.addWidget(bottom_widget)

        main_layout.addWidget(PanelCardBox("", content_inner, self))

    def _apply_theme(self, _=""):
        from .panel_theme import apply_layers_panel_theme
        apply_layers_panel_theme(self)
